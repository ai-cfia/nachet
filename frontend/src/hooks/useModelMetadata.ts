/**
 * useModelMetadata Hook
 *
 * Custom hook to load and manage ML model metadata.
 * Automatically fetches available models from the backend and sets the default model.
 */

import { useEffect } from "react";
import { useModelStore } from "@stores/useModelStore";
import { fetchModelMetadata } from "@common";

interface UseModelMetadataParams {
  backendUrl: string;
  isAuthenticated: boolean;
  authLoading: boolean;
}

export const useModelMetadata = ({
  backendUrl,
  isAuthenticated,
  authLoading,
}: UseModelMetadataParams) => {
  const { metadata, selectedModel, setMetadata, setSelectedModel, setLoading } =
    useModelStore();

  useEffect(() => {
    // Only load metadata if user is authenticated and no interaction is in progress
    if (!isAuthenticated || authLoading) {
      return;
    }

    const loadModelMetadata = async () => {
      try {
        setLoading(true);
        const metadata = await fetchModelMetadata({ backendUrl });
        setMetadata(metadata);

        // Find the default model from the metadata
        const defaultModel = metadata.find((model) => model.default);
        if (defaultModel) {
          setSelectedModel(defaultModel.pipelineId);
        }
      } catch (error) {
        console.error(
          "Error fetching model metadata:",
          error instanceof Error ? error.message : String(error),
        );
        alert("Error fetching model metadata, see console for details");
      } finally {
        setLoading(false);
      }
    };

    void loadModelMetadata();
  }, [
    authLoading,
    backendUrl,
    isAuthenticated,
    setMetadata,
    setSelectedModel,
    setLoading,
  ]);

  return { metadata, selectedModel };
};
