import { render, fireEvent } from "@testing-library/react";
import { describe, expect, vi, beforeEach, test } from "vitest";
import "@testing-library/jest-dom";
import StorageDirectoryContainer from "../StorageDirectoryContainer";
import { useFolderStore } from "@stores/useFolderStore";
import { useDirectoryModalStore } from "@stores/useDirectoryModalStore";

// Mock the Zustand stores
vi.mock("@stores/useFolderStore");
vi.mock("@stores/useDirectoryModalStore");

describe("StorageDirectoryContainer", () => {
  const mockAzureStorageDir = [
    {
      folderId: "testDir1ID",
      folderName: "testDir1",
      folderPrefix: "prefix1",
      description: "Test directory 1",
      pictureCount: 1,
    },
    {
      folderId: "testDir2ID",
      folderName: "testDir2",
      folderPrefix: "prefix2",
      description: "Test directory 2",
      pictureCount: 2,
    },
    {
      folderId: "testDir3ID",
      folderName: "testDir3",
      folderPrefix: "prefix3",
      description: "Test directory 3",
      pictureCount: 3,
    },
  ];

  const mockCurDir = {
    folderId: "testDirID",
    folderName: "testDir",
    folderPrefix: "testDir",
    description: "Test current directory",
    pictureCount: 0,
  };

  const mockSetCurDir = vi.fn();
  const mockOpenCreateDirectory = vi.fn();
  const mockOpenEditDirectory = vi.fn();
  const mockOpenDeleteDirectory = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock useFolderStore
    vi.mocked(useFolderStore).mockReturnValue({
      curDir: mockCurDir,
      setCurDir: mockSetCurDir,
      folderData: null,
      isLoading: false,
      error: null,
      setFolderData: vi.fn(),
      setLoading: vi.fn(),
      setError: vi.fn(),
      clearFolderData: vi.fn(),
      clearCurDir: vi.fn(),
    });

    // Mock useDirectoryModalStore
    vi.mocked(useDirectoryModalStore).mockReturnValue({
      createDirectoryOpen: false,
      editDirectoryOpen: false,
      delDirectoryOpen: false,
      editingFolder: null,
      openCreateDirectory: mockOpenCreateDirectory,
      closeCreateDirectory: vi.fn(),
      openEditDirectory: mockOpenEditDirectory,
      closeEditDirectory: vi.fn(),
      openDeleteDirectory: mockOpenDeleteDirectory,
      closeDeleteDirectory: vi.fn(),
      setEditingFolder: vi.fn(),
    });
  });

  test("should render directory items correctly", () => {
    const { getByTestId } = render(
      <StorageDirectoryContainer azureStorageDir={mockAzureStorageDir} />,
    );
    const directoryItem1 = getByTestId("folder-icon1");
    const directoryItem2 = getByTestId("folder-icon2");

    expect(directoryItem1).toBeInTheDocument();
    expect(directoryItem2).toBeInTheDocument();
    expect(directoryItem1.textContent).toContain("testDir1");
    expect(directoryItem2.textContent).toContain("testDir2");
  });

  test("should call handleDelete and setDelDirectoryOpen when delete button is clicked", () => {
    const { getByTestId } = render(
      <StorageDirectoryContainer azureStorageDir={mockAzureStorageDir} />,
    );
    for (let i = 1; i < mockAzureStorageDir.length + 1; i++) {
      const deleteButton = getByTestId("delete-icon" + i);
      fireEvent.click(deleteButton);
      expect(mockSetCurDir).toHaveBeenCalledWith(mockAzureStorageDir[i - 1]);
      expect(mockOpenDeleteDirectory).toHaveBeenCalled();
    }
  });

  test("should call handleSelect when folder is selected", () => {
    const { getByTestId } = render(
      <StorageDirectoryContainer azureStorageDir={mockAzureStorageDir} />,
    );
    for (let i = 1; i < mockAzureStorageDir.length + 1; i++) {
      const folderElement = getByTestId("folder-icon" + i);
      fireEvent.click(folderElement);
      expect(mockSetCurDir).toHaveBeenCalledWith(mockAzureStorageDir[i - 1]);
    }
  });

  test("should call handleCreateDirectory and setCurDir when create directory button is clicked", () => {
    const { getByTestId } = render(
      <StorageDirectoryContainer azureStorageDir={mockAzureStorageDir} />,
    );
    const createDirectoryButton = getByTestId("CreateNewFolderIcon");
    fireEvent.click(createDirectoryButton);
    expect(mockOpenCreateDirectory).toHaveBeenCalled();
    expect(mockSetCurDir).toHaveBeenCalledWith(null);
  });
});
