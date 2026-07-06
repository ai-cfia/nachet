// root\body\index.tsx
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import type Webcam from "react-webcam";
import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import { colours } from "../../styles/colours";
import {
  DirectoryPopup,
  BatchUploadPopup,
  AuthPopup,
  UploadPopup,
  CreativeCommonsPopup,
  SaveCapturePopup,
  ModelPopup,
  SwitchDevicePopup,
  SampleMetadataPopup,
  ImageMetadataPopup,
  ClassificationResults,
  ImageCache,
  StorageDirectory,
  MicroscopeFeed,
  RegistrationStatusPopup,
  NotificationLogPopup,
} from "@components/body";
import { ToastNotification } from "@components/common/ToastNotification";
import {
  useBackendUrl,
  useDecoderTiff,
  useDeviceData,
  useWebcamDevices,
  useModelMetadata,
} from "@hooks";
import { useWorkflowStore } from "@stores/useWorkflowStore";
import { useImageStore } from "@stores/useImageStore";
import { useModalStore } from "@stores/useModalStore";
import { useFolderStore } from "@stores/useFolderStore";
import { useDirectoryModalStore } from "@stores/useDirectoryModalStore";
import { useModelStore } from "@stores/useModelStore";
import { useNotificationStore } from "@stores/useNotificationStore";
import { useInferenceResultsStore } from "@stores/useInferenceResultsStore";
import { WorkflowQueueManager } from "../../services/WorkflowQueueManager";
import { useNachetAuth } from "@auth";
import {
  getLabelOccurrence,
  loadToCanvas,
  inferenceDirectRequest,
  readAzureStorageDir,
  checkUserRegistration,
  // requestUUID,
} from "@common";
import {
  AzureStorageDirectoryItem,
  AzureStorageDirectoryItemApi,
  BoxCSS,
} from "@common/types";
// import Cookies from "js-cookie";

interface params {
  windowSize: {
    width: number;
    height: number;
  };
  creativeCommonsPopupOpen: boolean;
  setCreativeCommonsPopupOpen: React.Dispatch<React.SetStateAction<boolean>>;
  handleCreativeCommonsAgreement: (agree: boolean) => void;
}

const Body: React.FC<params> = (props) => {
  const { t } = useTranslation("errors");
  const [readAzureStorage, setReadAzureStorage] = useState<boolean>(false);
  const [azureStorageDir, setAzureStorageDir] = useState<
    AzureStorageDirectoryItem[]
  >([]);
  const [freeformBox, setFreeformBox] = useState<BoxCSS | null>(null);
  const [freeformDragEnabled, setFreeformDragEnabled] = useState<boolean>(true);
  const webcamRef = useRef<Webcam>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isWebcamActive, setIsWebcamActive] = useState(true); // This state determines the visibility of the webcam
  const [isLoading, setIsLoading] = useState(false);
  const [showInference, setShowInference] = useState<boolean>(true);
  const [switchTable, setSwitchTable] = useState<boolean>(true);
  const [registrationCheckComplete, setRegistrationCheckComplete] =
    useState(false);
  const [registrationModalOpen, setRegistrationModalOpen] = useState(false);

  // Queue manager (singleton, persists across renders)
  const queueManagerRef = useRef<WorkflowQueueManager>(
    new WorkflowQueueManager(),
  );

  // Directory modal store
  const {
    createDirectoryOpen,
    editDirectoryOpen,
    delDirectoryOpen,
    editingFolder,
  } = useDirectoryModalStore();

  // Folder store
  const { curDir, setCurDir } = useFolderStore();

  // Workflow store actions
  const { addWorkflow, removeWorkflow, getWorkflowByImageIndex } =
    useWorkflowStore();

  // Image store
  const {
    images: imageCache,
    currentIndex: imageIndex,
    addCapturedImage,
    addWorkflowToImage,
    setImageId,
  } = useImageStore();

  // Modal store
  const {
    isSaveOpen,
    isBatchUploadOpen,
    isUploadOpen,
    isModelInfoOpen,
    isSampleMetadataOpen,
    isSwitchDeviceOpen,
    notificationLogOpen,
    imageFormat,
    imageLabel,
    saveIndividualImage,
    setImageFormat,
    setImageLabel,
    setSaveIndividualImage,
  } = useModalStore();

  // Notification store
  const { addError, addWarning } = useNotificationStore();

  // Derive imageTiff and labelOccurrences from store
  const currentImageData = useMemo(() => {
    return imageCache.find((img) => img.index === imageIndex);
  }, [imageCache, imageIndex]);

  const imageTiff = useMemo(() => {
    return currentImageData?.src.includes("image/tiff")
      ? currentImageData.src
      : "";
  }, [currentImageData]);

  // Get active inference result for label occurrences
  const labelOccurrences = useMemo(() => {
    if (!currentImageData?.activeWorkflowId) return {};

    const inferenceResult =
      useInferenceResultsStore
        .getState()
        .getResult(currentImageData.activeWorkflowId) ?? null;

    return getLabelOccurrence(inferenceResult);
  }, [currentImageData?.activeWorkflowId]);

  const decodedTiff = useDecoderTiff(imageTiff);
  const backendUrl = useBackendUrl();
  const {
    accounts,
    activeAccount,
    isAuthenticated,
    isLoading: authLoading,
  } = useNachetAuth();

  // Webcam devices hook
  useWebcamDevices();
  const uuid = activeAccount?.userId ?? "";
  const { devicesData } = useDeviceData(backendUrl);

  // Model metadata hook
  useModelMetadata({
    backendUrl,
    isAuthenticated,
    authLoading,
  });

  // Model store
  const { selectedModel, metadata: modelMetadata } = useModelStore();

  // Derive pipeline ID and name from selected model
  const { pipelineId, pipelineName } = useMemo(() => {
    // Find metadata for selected model
    const modelData = modelMetadata.find(
      (m) => m.pipelineId === selectedModel || m.pipelineName === selectedModel,
    );

    if (modelData) {
      return {
        pipelineId: modelData.pipelineId,
        pipelineName: modelData.pipelineName,
      };
    }

    // Fallback if metadata not found (use selectedModel as both)
    return {
      pipelineId: selectedModel,
      pipelineName: selectedModel,
    };
  }, [selectedModel, modelMetadata]);

  // Derive authPopupOpen from authentication state
  const authPopupOpen = useMemo(() => {
    return !isAuthenticated && !authLoading;
  }, [authLoading, isAuthenticated]);

  const captureFeed = (): void => {
    // takes screenshot of webcam feed and loads it to cache when capture button is pressed
    const src: string | null | undefined = webcamRef.current?.getScreenshot();
    if (src === null || src === undefined) {
      return;
    }
    addCapturedImage(src);
  };

  const pushImageToCache = (src: string): void => {
    // loads image to cache when image is uploaded (called from UploadPopup)
    addCapturedImage(src);
  };

  const handleDirectInference = (): void => {
    // makes a post request to the backend to get inference data for the current image
    if (!isAuthenticated) {
      addError(t("auth.signInRequired"), "auth");
      return;
    }
    if (authLoading) {
      addWarning(t("auth.inProgress"), 8000);
      return;
    }
    if (!curDir) {
      addWarning(t("directory.notSelected"), 8000);
      return;
    }
    if (curDir) {
      const imageObject = imageCache.find((item) => item.index === imageIndex);
      if (imageObject === undefined) {
        return;
      }

      const folderId = curDir.folderId;
      const folderName = curDir.folderName;

      setIsLoading(true);
      inferenceDirectRequest({
        backendUrl,
        selectedModel,
        imageObject,
        curDir: folderName,
        folderId: folderId,
      })
        .then((response) => {
          setReadAzureStorage(!readAzureStorage);
          // TODO: Handle direct inference results with new inference store
          // Direct inference is a legacy/testing endpoint
          console.log("Direct inference response:", response);
        })
        .catch((error) => {
          addError(t("inference.fetchFailed"), "inference");
          console.error(
            "Inference fetch failed:",
            error instanceof Error ? error.message : String(error),
          );
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  };

  const handleInferenceRequest = (): void => {
    // makes a post request to the backend to get inference data for the current image
    if (!isAuthenticated) {
      addError(t("auth.signInRequired"), "auth");
      return;
    }
    if (authLoading) {
      addWarning(t("auth.inProgress"), 8000);
      return;
    }
    if (!curDir) {
      addWarning(t("directory.notSelected"), 8000);
      return;
    }

    const imageObject = imageCache.find((item) => item.index === imageIndex);
    if (imageObject === undefined) {
      return;
    }

    // Check if workflow already exists for this image
    const existingWorkflow = getWorkflowByImageIndex(imageIndex);
    if (existingWorkflow) {
      console.log(`[Workflow] Image ${imageIndex} already has active workflow`);
      return;
    }

    // Get queue status
    const queueStatus = queueManagerRef.current.getStatus();
    const MAX_TOTAL = 11; // 1 active + 10 queued
    const totalCount =
      queueStatus.queueSize + (queueStatus.hasActiveWorkflow ? 1 : 0);

    if (totalCount >= MAX_TOTAL) {
      addWarning(t("queue.full"), 10000);
      return;
    }

    // Enqueue the request - manager will process it
    const imageId = imageObject.imageId?.toString() || "";
    queueManagerRef.current.enqueue(imageIndex, imageId);

    console.log(
      `[Workflow] Request enqueued for image ${imageIndex}. Queue size: ${queueStatus.queueSize + 1}`,
    );
  };

  // Configure queue manager when dependencies change
  useEffect(() => {
    if (!curDir || !isAuthenticated) {
      return;
    }

    queueManagerRef.current.configure({
      backendUrl,
      pipelineId,
      pipelineName,
      curDir,
      images: imageCache,
      workflowStore: {
        addWorkflow,
        updateWorkflowStatus: (workflowId, status, error, queuePosition) => {
          const workflow = useWorkflowStore.getState().getWorkflow(workflowId);
          if (workflow) {
            useWorkflowStore
              .getState()
              .updateWorkflowStatus(
                workflowId,
                status as any,
                error,
                queuePosition,
              );
          }
        },
        removeWorkflow,
      },
      setImageId,
      onComplete: (
        workflowId,
        imageIndex,
        results,
        pipelineId,
        pipelineName,
      ) => {
        console.log(
          `[Workflow] Workflow ${workflowId} completed for image ${imageIndex} with pipeline ${pipelineName}`,
        );

        // Get image_id for this image
        const image = imageCache.find((img) => img.index === imageIndex);
        if (!image?.imageId) {
          console.error(`[Workflow] Image not found for index ${imageIndex}`);
          return;
        }

        // Store results in inference results store
        useInferenceResultsStore
          .getState()
          .addResult(
            workflowId,
            image.imageId,
            results,
            pipelineId,
            pipelineName,
          );

        // Link workflow to image and set as active
        addWorkflowToImage(imageIndex, workflowId, true);
        useInferenceResultsStore
          .getState()
          .setActiveResult(image.imageId, workflowId);

        setReadAzureStorage(!readAzureStorage);

        // Remove workflow from store after completion
        setTimeout(() => {
          removeWorkflow(workflowId);
        }, 1000); // Keep for 1 second to show "completed" status
      },
      onError: (workflowId, imageIndex, error) => {
        // Extract readable error message
        const errorMessage =
          error instanceof Error ? error.message : String(error);

        // Look up image_id (UUID) from imageIndex
        const image = imageCache.find((img) => img.index === imageIndex);
        const imageId = image?.imageId || `index-${imageIndex}`;

        console.error(
          `[Workflow] Workflow ${workflowId} failed for image ${imageId}: ${errorMessage}`,
        );

        addError(
          t("inference.processingFailed", {
            workflowId,
            imageId,
            error: errorMessage,
          }),
          "inference",
        );
      },
    });
  }, [
    backendUrl,
    pipelineId,
    pipelineName,
    curDir,
    imageCache,
    isAuthenticated,
    readAzureStorage,
    addWorkflowToImage,
    setReadAzureStorage,
    addWorkflow,
    removeWorkflow,
    setImageId,
    t,
    addError,
  ]);

  const handleFreeformBoxChange = useCallback(
    (box: BoxCSS | null, dragEnabled: boolean) => {
      setFreeformBox(box);
      setFreeformDragEnabled(dragEnabled);
    },
    [],
  );

  useEffect(() => {
    const imageData = imageCache.find((img) => img.index === imageIndex);
    if (imageData === undefined) {
      return;
    }
    if (isWebcamActive) {
      return;
    }

    // Get inference result for drawing boxes
    const inferenceResult = imageData.activeWorkflowId
      ? (useInferenceResultsStore
          .getState()
          .getResult(imageData.activeWorkflowId) ?? null)
      : null;

    loadToCanvas(
      canvasRef,
      decodedTiff,
      imageData,
      inferenceResult,
      "all", // Always show all labels on canvas
      labelOccurrences,
      switchTable, // Sync with ClassificationResults toggle
      showInference,
      freeformBox,
      freeformDragEnabled,
    );
  }, [
    labelOccurrences,
    decodedTiff,
    imageCache,
    imageIndex,
    isWebcamActive,
    showInference,
    switchTable,
    freeformBox,
    freeformDragEnabled,
  ]);

  // Clear queue manager on unmount
  useEffect(() => {
    const manager = queueManagerRef.current;
    return () => {
      manager.clear();
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    if (authLoading) {
      return;
    }
    if (backendUrl == null || backendUrl === "") {
      console.error("Backend URL is undefined, null or empty.");
      return;
    }
    if (uuid == null || uuid === "") {
      return;
    }
    if (registrationCheckComplete) {
      return; // Only check once
    }

    const checkRegistration = async () => {
      try {
        const response = await checkUserRegistration({
          backendUrl,
        });

        if (!response.isRegistered) {
          setRegistrationModalOpen(true);
          // Don't proceed to load directories
        } else {
          setRegistrationCheckComplete(true);
        }
      } catch (error) {
        console.error(
          "Registration check failed:",
          error instanceof Error ? error.message : String(error),
        );
        addError(t("registration.checkFailed"), "registration");
      }
    };

    checkRegistration();
  }, [
    uuid,
    backendUrl,
    authLoading,
    isAuthenticated,
    registrationCheckComplete,
    t,
    addError,
  ]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    if (authLoading) {
      return;
    }
    if (backendUrl == null || backendUrl === "") {
      console.error("Backend URL is undefined, null or empty.");
      return;
    }
    if (uuid == null || uuid === "") {
      return;
    }
    if (!registrationCheckComplete) {
      return; // Wait for registration check to complete
    }

    const loadAzureStorageDir = async () => {
      try {
        const response = await readAzureStorageDir({ backendUrl });
        const directories: AzureStorageDirectoryItem[] = [];
        const folders = response.directories;
        folders.forEach((item: AzureStorageDirectoryItemApi) => {
          directories.push({
            folderId: item.id,
            folderName: item.name,
            folderPrefix: item.folderPrefix,
            description: item.description,
            pictureCount: item.pictureCount,
            isDefaultFolder: item.isDefaultFolder,
          });
        });
        setAzureStorageDir(directories);
      } catch (error) {
        console.error(
          "Storage read failed:",
          error instanceof Error ? error.message : String(error),
        );
        addError(t("storage.readFailed"), "storage");
      }
    };

    loadAzureStorageDir();
  }, [
    uuid,
    backendUrl,
    authLoading,
    isAuthenticated,
    registrationCheckComplete,
    readAzureStorage,
    t,
    addError,
  ]);

  // Auto-select user's default directory after directories are loaded
  useEffect(() => {
    if (!azureStorageDir || azureStorageDir.length === 0) {
      return;
    }

    // Don't override if user has already selected a folder
    if (curDir !== null) {
      return;
    }

    // Extract username from email and convert to lowercase
    const userEmail = accounts[0]?.username || "";
    const username = userEmail.split("@")[0].toLowerCase();

    // Find matching folder
    const defaultFolder = azureStorageDir.find(
      (folder) => folder.folderName.toLowerCase() === username,
    );

    if (defaultFolder) {
      setCurDir(defaultFolder);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [azureStorageDir, accounts]);

  return (
    <>
      <ToastNotification />
      <Box
        data-testid="body-component"
        sx={{
          background: colours.CFIA_Background_White,
          color: colours.CFIA_Font_Black,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 0,
          maxWidth: "100%",
          padding: "0px 1vw",
          position: "relative",
          marginTop: "1vh",
          marginBottom: "1vh",
        }}
      >
        {authPopupOpen && (
          <AuthPopup
            open={authPopupOpen}
            onClose={() => {
              /* Auth popup closes automatically when user is authenticated */
            }}
          />
        )}
        {registrationModalOpen && (
          <RegistrationStatusPopup
            userOid={uuid}
            setPopupOpen={setRegistrationModalOpen}
          />
        )}
        {isBatchUploadOpen && (
          <BatchUploadPopup
            backendUrl={backendUrl}
            uuid={uuid}
            containerName={uuid}
            setReadAzureStorage={setReadAzureStorage}
          />
        )}
        {createDirectoryOpen && (
          <DirectoryPopup
            setReadAzureStorage={setReadAzureStorage}
            mode="create"
          />
        )}
        {editDirectoryOpen && editingFolder && (
          <DirectoryPopup
            setReadAzureStorage={setReadAzureStorage}
            mode="edit"
            initialData={{
              folderId: editingFolder.folderId,
              folderName: editingFolder.folderName,
              description: editingFolder.description || "",
            }}
          />
        )}
        {delDirectoryOpen && curDir && (
          <DirectoryPopup
            setReadAzureStorage={setReadAzureStorage}
            mode="delete"
            initialData={{
              folderId: curDir.folderId,
              folderName: curDir.folderName,
              description: curDir.description || "",
            }}
          />
        )}
        {isSaveOpen && (
          <SaveCapturePopup
            imageFormat={imageFormat}
            imageLabel={imageLabel}
            setImageFormat={setImageFormat}
            setImageLabel={setImageLabel}
            setSaveIndividualImage={setSaveIndividualImage}
            saveIndividualImage={saveIndividualImage}
          />
        )}
        {isUploadOpen && <UploadPopup pushImageToCache={pushImageToCache} />}
        {isModelInfoOpen && <ModelPopup />}
        {isSwitchDeviceOpen && <SwitchDevicePopup />}
        {isSampleMetadataOpen && (
          <SampleMetadataPopup devicesData={devicesData} />
        )}
        <ImageMetadataPopup devicesData={devicesData} />
        {notificationLogOpen && <NotificationLogPopup />}
        {props.creativeCommonsPopupOpen && (
          <CreativeCommonsPopup
            setCreativeCommonsPopupOpen={props.setCreativeCommonsPopupOpen}
            handleCreativeCommonsAgreement={
              props.handleCreativeCommonsAgreement
            }
          />
        )}

        <Box
          data-testid="body-two-column-container"
          sx={{
            background: colours.CFIA_Background_White,
            color: colours.CFIA_Font_Black,
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            justifyContent: "flex-start",
            alignItems: "center",
            width: "100%",
            maxWidth: "100%",
            // minHeight: "80vh",
            minHeight: { xs: "50vh", md: "80vh" },
            position: "relative",
            zIndex: 0,
            padding: "0px 0px 0px 1vw",
          }}
        >
          <Box
            data-testid="body-left-column"
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              // width: "60%",
              // maxWidth: "60%",
              minHeight: { xs: "50vh", md: "80vh" },
              maxHeight: { xs: "50vh", md: "80vh" },
              zIndex: 0,
              position: "relative",
              paddingBottom: { xs: "2vh", md: 0 },
              paddingLeft: { xs: "2vw", md: 0 },
              paddingRight: { xs: "2vw", md: 0 },
            }}
          >
            <MicroscopeFeed
              capture={captureFeed}
              webcamRef={webcamRef}
              windowSize={props.windowSize}
              isLoading={isLoading}
              canvasRef={canvasRef}
              handleInference={handleInferenceRequest}
              handleDirectInference={handleDirectInference}
              isWebcamActive={isWebcamActive}
              onCaptureClick={() => {
                setIsWebcamActive(!isWebcamActive);
              }}
              toggleShowInference={(state: boolean) => setShowInference(state)}
              onFreeformBoxChange={handleFreeformBoxChange}
              backendUrl={backendUrl}
              uuid={uuid}
            />
          </Box>
          <Box
            data-testid="body-right-column"
            sx={{
              display: "flex",
              flexDirection: "column",
              // alignItems: "start",
              alignItems: { xs: "flex-end", md: "flex-start" },
              justifyContent: "space-between",
              minWidth: { xs: "100%", md: "23vw" },
              maxWidth: { xs: "100%", md: "23vw" },
              // minHeight: "80vh",
              // maxHeight: "100%",
              minHeight: { xs: "50vh", md: "80vh" },
              maxHeight: { xs: "50vh", md: "80vh" },
              zIndex: 0,
              position: "relative",
              paddingLeft: { xs: "2vw", md: "1vw" },
              paddingRight: { xs: "2vw", md: 0 },
            }}
          >
            <StorageDirectory azureStorageDir={azureStorageDir} />
            <ImageCache />
            <ClassificationResults
              labelOccurrences={labelOccurrences}
              switchTable={switchTable}
              onSwitchTableChange={setSwitchTable}
            />
          </Box>
        </Box>
      </Box>
    </>
  );
};

export default Body;
