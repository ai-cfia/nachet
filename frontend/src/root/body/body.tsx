// root\body\index.tsx
import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import type Webcam from "react-webcam";
import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import { colours } from "../../styles/colours";
import {
  CreateDirectoryPopup,
  BatchUploadPopup,
  DeleteDirectoryPopup,
  AuthPopup,
  UploadPopup,
  CreativeCommonsPopup,
  SaveCapturePopup,
  ModelPopup,
  SwitchDevicePopup,
  DeviceInfoPopup,
  ClassificationResults,
  ImageCache,
  StorageDirectory,
  MicroscopeFeed,
  RegistrationStatusPopup,
} from "@components/body";
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
import { WorkflowQueueManager } from "../../services/WorkflowQueueManager";
import { InteractionStatus } from "@azure/msal-browser";
import { useMsal, useIsAuthenticated, useAccount } from "@azure/msal-react";
import { acquireAccessToken } from "@common/auth";
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
  apiScopeClaim: string;
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
    loadInferenceResults,
    setImageId,
  } = useImageStore();

  // Modal store
  const {
    isSaveOpen,
    isBatchUploadOpen,
    isUploadOpen,
    isModelInfoOpen,
    isDeviceInfoOpen,
    isSwitchDeviceOpen,
    imageFormat,
    imageLabel,
    saveIndividualImage,
    setImageFormat,
    setImageLabel,
    setSaveIndividualImage,
  } = useModalStore();

  // Derive imageTiff and labelOccurrences from store
  const currentImageData = useMemo(() => {
    return imageCache.find((img) => img.index === imageIndex);
  }, [imageCache, imageIndex]);

  const imageTiff = useMemo(() => {
    return currentImageData?.src.includes("image/tiff")
      ? currentImageData.src
      : "";
  }, [currentImageData]);

  const labelOccurrences = useMemo(() => {
    return currentImageData ? getLabelOccurrence(currentImageData) : {};
  }, [currentImageData]);

  const decodedTiff = useDecoderTiff(imageTiff);
  const backendUrl = useBackendUrl();
  const apiScopeClaim = props.apiScopeClaim;
  const { instance: msalInstance, inProgress, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const accountInfo = useAccount();

  // Webcam devices hook
  useWebcamDevices();
  const uuid = accountInfo?.idTokenClaims?.oid ?? "";
  const { devicesData } = useDeviceData(backendUrl, apiScopeClaim);

  // Model metadata hook
  useModelMetadata({
    backendUrl,
    apiScopeClaim,
    isAuthenticated,
    inProgress,
  });

  // Model store
  const { selectedModel } = useModelStore();

  // Derive authPopupOpen from authentication state
  const authPopupOpen = useMemo(() => {
    return !isAuthenticated && inProgress === InteractionStatus.None;
  }, [isAuthenticated, inProgress]);

  // Set active account if available
  useEffect(() => {
    if (accounts.length > 0 && !msalInstance.getActiveAccount()) {
      msalInstance.setActiveAccount(accounts[0]);
    }
  }, [accounts, msalInstance]);

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
      alert(t("auth.signInRequired"));
      return;
    }
    if (inProgress !== InteractionStatus.None) {
      alert(t("auth.inProgress"));
      return;
    }
    if (!curDir) {
      alert(t("directory.notSelected"));
      return;
    }
    if (curDir) {
      const imageObject = imageCache.find((item) => item.index === imageIndex);
      if (imageObject === undefined) {
        return;
      }

      const folder_id = curDir.folderId;
      const folder_name = curDir.folderName;

      setIsLoading(true);
      acquireAccessToken(msalInstance, [apiScopeClaim])
        .then((accessToken) => {
          return inferenceDirectRequest({
            backendUrl,
            selectedModel,
            imageObject,
            curDir: folder_name,
            accessToken,
            folder_id: folder_id,
          });
        })
        .then((response) => {
          setReadAzureStorage(!readAzureStorage);
          loadInferenceResults(response, imageIndex, selectedModel);
        })
        .catch((error) => {
          alert(t("inference.fetchFailed"));
          console.error(error);
        })
        .finally(() => {
          setIsLoading(false);
        });
    }
  };

  const handleInferenceRequest = (): void => {
    // makes a post request to the backend to get inference data for the current image
    if (!isAuthenticated) {
      alert(t("auth.signInRequired"));
      return;
    }
    if (inProgress !== InteractionStatus.None) {
      alert(t("auth.inProgress"));
      return;
    }
    if (!curDir) {
      alert(t("directory.notSelected"));
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
      alert(t("queue.full"));
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

    const scopes = apiScopeClaim ? [apiScopeClaim] : [];

    queueManagerRef.current.configure({
      backendUrl,
      msalInstance,
      scopes,
      selectedModel,
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
      onComplete: (workflowId, imageIndex, results) => {
        console.log(
          `[Workflow] Workflow ${workflowId} completed for image ${imageIndex}`,
        );
        // Apply results to the correct image
        loadInferenceResults(results, imageIndex, selectedModel);
        setReadAzureStorage(!readAzureStorage);

        // Remove workflow from store after completion
        setTimeout(() => {
          removeWorkflow(workflowId);
        }, 1000); // Keep for 1 second to show "completed" status
      },
      onError: (workflowId, imageIndex, error) => {
        console.error(
          `[Workflow] Workflow ${workflowId} failed for image ${imageIndex}:`,
          error,
        );
        alert(t("inference.processingFailed"));
      },
    });
  }, [
    backendUrl,
    msalInstance,
    apiScopeClaim,
    selectedModel,
    curDir,
    imageCache,
    isAuthenticated,
    readAzureStorage,
    loadInferenceResults,
    setReadAzureStorage,
    addWorkflow,
    removeWorkflow,
    setImageId,
    t,
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
    loadToCanvas(
      canvasRef,
      decodedTiff,
      imageData,
      "all", // Always show all labels on canvas
      labelOccurrences,
      true, // Always use label occurrence view on canvas
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
    if (inProgress !== InteractionStatus.None) {
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
        const accessToken = await acquireAccessToken(msalInstance, [
          apiScopeClaim,
        ]);
        const response = await checkUserRegistration({
          backendUrl,
          accessToken,
        });

        if (!response.is_registered) {
          setRegistrationModalOpen(true);
          // Don't proceed to load directories
        } else {
          setRegistrationCheckComplete(true);
        }
      } catch (error) {
        console.error(error);
        alert(t("registration.checkFailed"));
      }
    };

    checkRegistration();
  }, [
    uuid,
    backendUrl,
    msalInstance,
    apiScopeClaim,
    isAuthenticated,
    inProgress,
    registrationCheckComplete,
    t,
  ]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    if (inProgress !== InteractionStatus.None) {
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
        const accessToken = await acquireAccessToken(msalInstance, [
          apiScopeClaim,
        ]);
        const response = await readAzureStorageDir({ backendUrl, accessToken });
        const directories: AzureStorageDirectoryItem[] = [];
        const folders = response.directories;
        folders.forEach((item: AzureStorageDirectoryItemApi) => {
          directories.push({
            folderId: item.id,
            folderName: item.name,
            folderPrefix: item.folder_prefix,
            description: item.description,
            pictureCount: item.picture_count,
            isDefaultFolder: item.is_default_folder,
          });
        });
        setAzureStorageDir(directories);
      } catch (error) {
        console.error(error);
        alert(t("storage.readFailed"));
      }
    };

    loadAzureStorageDir();
  }, [
    uuid,
    backendUrl,
    msalInstance,
    apiScopeClaim,
    isAuthenticated,
    inProgress,
    registrationCheckComplete,
    readAzureStorage,
    t,
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
          apiScopeClaim={apiScopeClaim}
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
          apiScopeClaim={apiScopeClaim}
        />
      )}
      {delDirectoryOpen && (
        <DeleteDirectoryPopup
          setReadAzureStorage={setReadAzureStorage}
          apiScopeClaim={apiScopeClaim}
        />
      )}
      {createDirectoryOpen && (
        <CreateDirectoryPopup
          setReadAzureStorage={setReadAzureStorage}
          apiScopeClaim={apiScopeClaim}
          mode="create"
        />
      )}
      {editDirectoryOpen && editingFolder && (
        <CreateDirectoryPopup
          setReadAzureStorage={setReadAzureStorage}
          apiScopeClaim={apiScopeClaim}
          mode="edit"
          initialData={{
            folderId: editingFolder.folderId,
            folderName: editingFolder.folderName,
            description: editingFolder.description || "",
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
      {isDeviceInfoOpen && <DeviceInfoPopup devicesData={devicesData} />}
      {props.creativeCommonsPopupOpen && (
        <CreativeCommonsPopup
          setCreativeCommonsPopupOpen={props.setCreativeCommonsPopupOpen}
          handleCreativeCommonsAgreement={props.handleCreativeCommonsAgreement}
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
          minHeight: "80vh",
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
            minHeight: "80vh",
            zIndex: 0,
            position: "relative",
            paddingBottom: { xs: "2vh", md: 0 },
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
            apiScopeClaim={apiScopeClaim}
          />
        </Box>
        <Box
          data-testid="body-right-column"
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "start",
            justifyContent: "space-between",
            minWidth: { xs: "100%", md: "23vw" },
            maxWidth: { xs: "100%", md: "23vw" },
            minHeight: "80vh",
            maxHeight: "100%",
            zIndex: 0,
            position: "relative",
            paddingLeft: "1vw",
          }}
        >
          <StorageDirectory azureStorageDir={azureStorageDir} />
          <ImageCache />
          <ClassificationResults labelOccurrences={labelOccurrences} />
        </Box>
      </Box>
    </Box>
  );
};

export default Body;
