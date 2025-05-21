import { render, fireEvent } from "@testing-library/react";
import { describe, expect, vi } from "vitest";
import "@testing-library/jest-dom";
import StorageDirectoryContainer from "../StorageDirectoryContainer";

describe("StorageDirectoryContainer", () => {
  const mockProps = {
    azureStorageDir: [
      {
        folderName: "testDir1",
        nbPictures: 1,
        pictureSetId: "testDir1ID",
        pictures: [
          {
            inferenceExists: false,
            isValidation: false,
            pictureId: "testDir1Pic1",
          },
        ],
      },
      {
        folderName: "testDir2",
        nbPictures: 2,
        pictureSetId: "testDir2ID",
        pictures: [
          {
            inferenceExists: false,
            isValidation: false,
            pictureId: "testDir2Pic1",
          },
          {
            inferenceExists: false,
            isValidation: false,
            pictureId: "testDir2Pic2",
          },
        ],
      },
      {
        folderName: "testDir3",
        nbPictures: 3,
        pictureSetId: "testDir3ID",
        pictures: [
          {
            inferenceExists: false,
            isValidation: false,
            pictureId: "testDir3Pic1",
          },
          {
            inferenceExists: false,
            isValidation: false,
            pictureId: "testDir3Pic2",
          },
          {
            inferenceExists: false,
            isValidation: false,
            pictureId: "testDir3Pic3",
          },
        ],
      },
    ],
    curDir: "testDir",
    setCurDir: vi.fn(),
    setCreateDirectoryOpen: vi.fn(),
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
        "testDir" + i + "ID",
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
        "testDir" + i + "ID",
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
    expect(mockProps.setCurDir).toHaveBeenCalledWith("");
  });
});
