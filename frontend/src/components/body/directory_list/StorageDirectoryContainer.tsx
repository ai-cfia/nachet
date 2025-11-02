import { AzureStorageDirectoryItem } from "@common/types";
import { useFolderStore } from "@stores/useFolderStore";
import { useDirectoryModalStore } from "@stores/useDirectoryModalStore";
import StorageDirectoryView from "./StorageDirectoryView";

export interface params {
  azureStorageDir: AzureStorageDirectoryItem[];
}

const StorageDirectoryContainer: React.FC<params> = (props) => {
  const { curDir, setCurDir } = useFolderStore();
  const { openCreateDirectory, openEditDirectory, openDeleteDirectory } =
    useDirectoryModalStore();

  const handleDelete = (folder: string): void => {
    const selectedDir =
      props.azureStorageDir.find((item) => item.folderId === folder) ?? null;
    setCurDir(selectedDir);
    openDeleteDirectory();
  };

  const handleSelect = (folder: string): void => {
    const selectedDir =
      props.azureStorageDir.find((item) => item.folderId === folder) ?? null;
    if (folder === curDir?.folderId) {
      setCurDir(null);
    } else {
      setCurDir(selectedDir);
    }
  };

  const handleCreateDirectory = (): void => {
    openCreateDirectory();
    setCurDir(null);
  };

  const handleEdit = (folder: string): void => {
    const selectedDir =
      props.azureStorageDir.find((item) => item.folderId === folder) ?? null;
    if (selectedDir) {
      openEditDirectory(selectedDir);
    }
  };

  return (
    <StorageDirectoryView
      azureStorageDir={props.azureStorageDir}
      curDir={curDir}
      handleSelect={handleSelect}
      handleDelete={handleDelete}
      handleEdit={handleEdit}
      handleCreateDirectory={handleCreateDirectory}
    />
  );
};

export default StorageDirectoryContainer;
