import { AzureStorageDirectoryItem } from "@common/types";
import StorageDirectoryView from "./StorageDirectoryView";

export interface params {
  azureStorageDir: AzureStorageDirectoryItem[];
  curDir: AzureStorageDirectoryItem | null;
  setCurDir: React.Dispatch<
    React.SetStateAction<AzureStorageDirectoryItem | null>
  >;
  setCreateDirectoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setDelDirectoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  handleDirChange: (dir: AzureStorageDirectoryItem | null) => void;
}

const StorageDirectoryContainer: React.FC<params> = (props) => {
  const handleDelete = (folder: string): void => {
    const selectedDir =
      props.azureStorageDir.find((item) => item.folderId === folder) ?? null;
    props.handleDirChange(selectedDir);
    props.setDelDirectoryOpen(true);
  };
  const handleSelect = (folder: string): void => {
    const selectedDir =
      props.azureStorageDir.find((item) => item.folderId === folder) ?? null;
    if (folder === props.curDir?.folderId) {
      props.handleDirChange(null);
    } else {
      props.handleDirChange(selectedDir);
    }
  };
  const handleCreateDirectory = (): void => {
    props.setCreateDirectoryOpen(true);
    props.setCurDir(null);
  };

  return (
    <StorageDirectoryView
      azureStorageDir={props.azureStorageDir}
      curDir={props.curDir}
      handleSelect={handleSelect}
      handleDelete={handleDelete}
      handleCreateDirectory={handleCreateDirectory}
    />
  );
};

export default StorageDirectoryContainer;
