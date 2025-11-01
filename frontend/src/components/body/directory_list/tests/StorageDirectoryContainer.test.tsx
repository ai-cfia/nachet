import { render, fireEvent } from "@testing-library/react";
import { describe, expect, vi, beforeEach, test } from "vitest";
import "@testing-library/jest-dom";
import StorageDirectoryContainer from "../StorageDirectoryContainer";

describe("StorageDirectoryContainer", () => {
  const mockProps = {
    azureStorageDir: [
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
    ],
    curDir: {
      folderId: "testDirID",
      folderName: "testDir",
      folderPrefix: "testDir",
      description: "Test current directory",
      pictureCount: 0,
    },
    setCurDir: vi.fn(),
    setCreateDirectoryOpen: vi.fn(),
    setEditDirectoryOpen: vi.fn(),
    setEditingFolder: vi.fn(),
    setDelDirectoryOpen: vi.fn(),
    handleDirChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("should render directory items correctly", () => {
    const { getByTestId } = render(
      <StorageDirectoryContainer {...mockProps} />,
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
      <StorageDirectoryContainer {...mockProps} />,
    );
    for (
      let i = 1;
      i < Object.keys(mockProps.azureStorageDir).length + 1;
      i++
    ) {
      const deleteButton = getByTestId("delete-icon" + i);
      fireEvent.click(deleteButton);
      expect(mockProps.handleDirChange).toHaveBeenCalledWith(
        mockProps.azureStorageDir[i - 1],
      );
      expect(mockProps.setDelDirectoryOpen).toHaveBeenCalledWith(true);
    }
  });

  test("should call handleSelect when folder is selected", () => {
    const { getByTestId } = render(
      <StorageDirectoryContainer {...mockProps} />,
    );
    for (
      let i = 1;
      i < Object.keys(mockProps.azureStorageDir).length + 1;
      i++
    ) {
      const folderElement = getByTestId("folder-icon" + i);
      fireEvent.click(folderElement);
      expect(mockProps.handleDirChange).toHaveBeenCalledWith(
        mockProps.azureStorageDir[i - 1],
      );
    }
  });

  test("should call handleCreateDirectory and setCurDir when create directory button is clicked", () => {
    const { getByTestId } = render(
      <StorageDirectoryContainer {...mockProps} />,
    );
    const createDirectoryButton = getByTestId("CreateNewFolderIcon");
    fireEvent.click(createDirectoryButton);
    expect(mockProps.setCreateDirectoryOpen).toHaveBeenCalledWith(true);
    expect(mockProps.setCurDir).toHaveBeenCalledWith(null);
  });
});
