/**
 * Folder Data Hook
 *
 * Custom hook to fetch and cache folder data.
 * Follows the pattern established by useSpeciesData.
 */

import { useEffect } from "react";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { useFolderStore, FolderData } from "@stores/useFolderStore";
import { readAzureStorageDir } from "@common/api";
import { acquireAccessToken } from "@common/auth";

export const useFolderData = (backendUrl: string, apiScopeClaim: string) => {
  const { folderData, isLoading, error, setFolderData, setLoading, setError } =
    useFolderStore();
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  useEffect(() => {
    const fetchFolderData = async () => {
      if (!backendUrl || backendUrl === "") {
        return;
      }

      if (!isAuthenticated) {
        return; // Must be authenticated first
      }

      if (folderData) {
        return; // Already have data, don't fetch again
      }

      if (inProgress !== InteractionStatus.None) {
        return; // Wait for interaction to complete
      }

      setLoading(true);
      setError(null);

      try {
        const accessToken = await acquireAccessToken(instance, [apiScopeClaim]);
        const response = await readAzureStorageDir({ backendUrl, accessToken });

        // Transform API response to match store format
        const directories: FolderData[] = response.directories.map((item) => ({
          folderId: item.id,
          folderName: item.name,
          folderPrefix: item.folderPrefix,
          description: item.description || "",
          pictureCount: item.pictureCount,
          isDefaultFolder: item.isDefaultFolder,
        }));

        setFolderData({ directories });
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);
        console.error("Error fetching folder data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchFolderData();
  }, [
    apiScopeClaim,
    backendUrl,
    instance,
    inProgress,
    isAuthenticated,
    setError,
    setLoading,
    setFolderData,
    folderData,
  ]);

  return {
    folderData,
    isLoading,
    error,
  };
};
