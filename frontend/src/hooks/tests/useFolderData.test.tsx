import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useFolderData } from "../useFolderData";
import { useFolderStore, FolderData } from "@stores/useFolderStore";
import { readAzureStorageDir } from "@common/api";
import { acquireAccessToken, isAppAuthenticated } from "@common/auth";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";

// Mock dependencies
vi.mock("@stores/useFolderStore");
vi.mock("@common/api");
vi.mock("@common/auth");
vi.mock("@azure/msal-react");

describe("useFolderData", () => {
  let mockSetFolderData: any;
  let mockSetLoading: any;
  let mockSetError: any;
  let mockMsalInstance: any;
  const mockApiResponse = {
    directories: [
      {
        id: "folder-1",
        name: "Folder 1",
        folderPrefix: "prefix1",
        description: "Description 1",
        pictureCount: 10,
      },
      {
        id: "folder-2",
        name: "Folder 2",
        folderPrefix: "prefix2",
        description: "",
        pictureCount: 5,
      },
    ],
  };

  const expectedFolderData: FolderData[] = [
    {
      folderId: "folder-1",
      folderName: "Folder 1",
      folderPrefix: "prefix1",
      description: "Description 1",
      pictureCount: 10,
    },
    {
      folderId: "folder-2",
      folderName: "Folder 2",
      folderPrefix: "prefix2",
      description: "",
      pictureCount: 5,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    mockSetFolderData = vi.fn();
    mockSetLoading = vi.fn();
    mockSetError = vi.fn();
    mockMsalInstance = {} as any;

    (useFolderStore as any).mockReturnValue({
      folderData: null,
      isLoading: false,
      error: null,
      setFolderData: mockSetFolderData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.None,
    });

    (useIsAuthenticated as any).mockReturnValue(true);
    (isAppAuthenticated as any).mockImplementation(
      (isMsalAuthenticated: boolean) => isMsalAuthenticated,
    );
    (acquireAccessToken as any).mockResolvedValue("test-token");
    (readAzureStorageDir as any).mockResolvedValue(mockApiResponse);

    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("should fetch and transform folder data when authenticated", async () => {
    renderHook(() => useFolderData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(null);
    });

    await waitFor(() => {
      expect(readAzureStorageDir).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
        accessToken: "test-token",
      });
    });

    await waitFor(() => {
      expect(mockSetFolderData).toHaveBeenCalledWith({
        directories: expectedFolderData,
      });
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should handle missing description field", async () => {
    const apiResponseWithoutDescription = {
      directories: [
        {
          id: "folder-1",
          name: "Folder 1",
          folderPrefix: "prefix1",
          pictureCount: 10,
        },
      ],
    };

    (readAzureStorageDir as any).mockResolvedValue(
      apiResponseWithoutDescription,
    );

    renderHook(() => useFolderData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetFolderData).toHaveBeenCalledWith({
        directories: [
          {
            folderId: "folder-1",
            folderName: "Folder 1",
            folderPrefix: "prefix1",
            description: "",
            pictureCount: 10,
          },
        ],
      });
    });
  });

  it("should not fetch when backendUrl is empty", () => {
    renderHook(() => useFolderData("", "test-scope"));
    expect(readAzureStorageDir).not.toHaveBeenCalled();
  });

  it("should not fetch when not authenticated", () => {
    (useIsAuthenticated as any).mockReturnValue(false);
    renderHook(() => useFolderData("http://test-backend.com", "test-scope"));
    expect(readAzureStorageDir).not.toHaveBeenCalled();
  });

  it("should not fetch when data already exists", () => {
    (useFolderStore as any).mockReturnValue({
      folderData: { directories: expectedFolderData },
      isLoading: false,
      error: null,
      setFolderData: mockSetFolderData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    renderHook(() => useFolderData("http://test-backend.com", "test-scope"));
    expect(readAzureStorageDir).not.toHaveBeenCalled();
  });

  it("should not fetch when interaction is in progress", () => {
    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.Login,
    });

    renderHook(() => useFolderData("http://test-backend.com", "test-scope"));
    expect(readAzureStorageDir).not.toHaveBeenCalled();
  });

  it("should handle errors", async () => {
    const mockError = new Error("Failed to fetch folders");
    (readAzureStorageDir as any).mockRejectedValue(mockError);

    renderHook(() => useFolderData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith("Failed to fetch folders");
      expect(console.error).toHaveBeenCalled();
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should handle non-Error rejection", async () => {
    (readAzureStorageDir as any).mockRejectedValue("String error");

    renderHook(() => useFolderData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith("Unknown error occurred");
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should return folderData, isLoading, and error from store", () => {
    const mockFolderData = { directories: expectedFolderData };

    (useFolderStore as any).mockReturnValue({
      folderData: mockFolderData,
      isLoading: true,
      error: "Test error",
      setFolderData: mockSetFolderData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    const { result } = renderHook(() =>
      useFolderData("http://test-backend.com", "test-scope"),
    );

    expect(result.current.folderData).toEqual(mockFolderData);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe("Test error");
  });
});
