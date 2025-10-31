// root\body\index.tsx
import { useState, useRef, useEffect, useMemo } from "react";
import type Webcam from "react-webcam";
import { Box } from "@mui/material";
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
import { useBackendUrl, useDecoderTiff, useDeviceData } from "@hooks";
import { useWorkflowStore } from "../../stores/useWorkflowStore";
import { useImageStore } from "../../stores/useImageStore";
import { WorkflowQueueManager } from "../../services/WorkflowQueueManager";
import {
  InteractionRequiredAuthError,
  InteractionStatus,
  InteractionType,
} from "@azure/msal-browser";
import {
  useMsal,
  useIsAuthenticated,
  useMsalAuthentication,
  useAccount,
} from "@azure/msal-react";
import { acquireAccessToken } from "@common/auth";
import {
  getLabelOccurrence,
  loadToCanvas,
  fetchModelMetadata,
  inferenceDirectRequest,
  readAzureStorageDir,
  checkUserRegistration,
  // requestUUID,
} from "@common";
import {
  AzureStorageDirectoryItem,
  AzureStorageDirectoryItemApi,
  ModelMetadata,
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
  const defaultImageSrc =
    "https://ai-cfia.github.io/nachet-frontend/placeholder-image.jpg";
  const [imageFormat, setImageFormat] = useState<string>("image/png");
  const [imageLabel, setImageLabel] = useState<string>("");
  const [saveOpen, setSaveOpen] = useState(false);
  const [batchUploadOpen, setBatchUploadOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [modelInfoPopupOpen, setModelInfoPopupOpen] = useState(false);
  const [switchDeviceOpen, setSwitchDeviceOpen] = useState(false);
  const [deviceInfoOpen, setDeviceInfoOpen] = useState(false);
  const [createDirectoryOpen, setCreateDirectoryOpen] = useState(false);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [activeDeviceId, setActiveDeviceId] = useState<string | undefined>(
    undefined,
  );
  const [curDir, setCurDir] = useState<AzureStorageDirectoryItem | null>(null);
  const [readAzureStorage, setReadAzureStorage] = useState<boolean>(false);
  const [azureStorageDir, setAzureStorageDir] = useState<
    AzureStorageDirectoryItem[]
  >([]);
  const [delDirectoryOpen, setDelDirectoryOpen] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState("Swin transformer");
  const [modelDisplayName, setModelDisplayName] = useState("");
  const [selectedLabel, setSelectedLabel] = useState<string>("all");
  const [saveIndividualImage, setSaveIndividualImage] = useState<string>("0");
  const [switchTable, setSwitchTable] = useState<boolean>(true);
  const webcamRef = useRef<Webcam>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isWebcamActive, setIsWebcamActive] = useState(true); // This state determines the visibility of the webcam
  const [isLoading, setIsLoading] = useState(false);
  const [metadata, setMetadata] = useState<ModelMetadata[]>([]);
  const [showInference, setShowInference] = useState<boolean>(true);
  const [registrationCheckComplete, setRegistrationCheckComplete] =
    useState(false);
  const [registrationModalOpen, setRegistrationModalOpen] = useState(false);
  const [accessToken, setAccessToken] = useState<string>("");

  // Queue manager (singleton, persists across renders)
  const queueManagerRef = useRef<WorkflowQueueManager>(
    new WorkflowQueueManager(),
  );

  // Workflow store actions
  const { addWorkflow, removeWorkflow, getWorkflowByImageIndex } =
    useWorkflowStore();

  // Image store
  const {
    images: imageCache,
    currentIndex: imageIndex,
    addCapturedImage,
    loadInferenceResults,
  } = useImageStore();

  // Derive imageSrc, imageTiff, and labelOccurrences from store
  const currentImageData = useMemo(() => {
    return imageCache.find((img) => img.index === imageIndex);
  }, [imageCache, imageIndex]);

  const imageSrc = useMemo(() => {
    return currentImageData?.src ?? defaultImageSrc;
  }, [currentImageData, defaultImageSrc]);

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
  const uuid = accountInfo?.idTokenClaims?.oid ?? "";
  const { devicesData } = useDeviceData(backendUrl, apiScopeClaim);

  // Derive authPopupOpen from authentication state
  const authPopupOpen = useMemo(() => {
    return !isAuthenticated && inProgress === InteractionStatus.None;
  }, [isAuthenticated, inProgress]);

  const authRequest = useMemo(() => {
    return {
      scopes: [apiScopeClaim ?? ""],
    };
  }, [apiScopeClaim]);

  const { login, error } = useMsalAuthentication(
    InteractionType.Silent,
    authRequest,
  );

  useEffect(() => {
    if (error instanceof InteractionRequiredAuthError) {
      login(InteractionType.Redirect, authRequest);
    }
    msalInstance.setActiveAccount(accounts[0]);
  }, [accounts, authRequest, error, login, msalInstance]);

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

  const handleDirChange = (dir: AzureStorageDirectoryItem | null): void => {
    setCurDir(dir);
  };

  const handleDirectInference = (): void => {
    // makes a post request to the backend to get inference data for the current image
    if (!isAuthenticated) {
      alert("You must be signed in to perform inference");
      return;
    }
    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
      return;
    }
    if (!curDir) {
      alert("Please select a directory");
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
          loadInferenceResults(response, imageIndex);
          setModelDisplayName(selectedModel);
        })
        .catch((error) => {
          alert("Error fetching inference data, see console for details");
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
      alert("You must be signed in to perform inference");
      return;
    }
    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
      return;
    }
    if (!curDir) {
      alert("Please select a directory");
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
      alert("Queue is full (10 items max). Please wait for some to complete.");
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
    if (!curDir || !accessToken || !isAuthenticated) {
      return;
    }

    queueManagerRef.current.configure({
      backendUrl,
      accessToken,
      selectedModel,
      curDir,
      images: imageCache,
      onComplete: (workflowId, imageIndex, results) => {
        console.log(
          `[Workflow] Workflow ${workflowId} completed for image ${imageIndex}`,
        );
        // Apply results to the correct image
        loadInferenceResults(results, imageIndex);
        setReadAzureStorage(!readAzureStorage);
        setModelDisplayName(selectedModel);

        // Add workflow to store for display/tracking
        addWorkflow(workflowId, results.imageId, imageIndex);
        // Remove it immediately (just for display purposes, no polling)
        removeWorkflow(workflowId);
      },
      onError: (workflowId, imageIndex, error) => {
        console.error(
          `[Workflow] Workflow ${workflowId} failed for image ${imageIndex}:`,
          error,
        );
        alert("Error processing inference, see console for details");
      },
    });
  }, [
    backendUrl,
    accessToken,
    selectedModel,
    curDir,
    imageCache,
    isAuthenticated,
    readAzureStorage,
    loadInferenceResults,
    setReadAzureStorage,
    setModelDisplayName,
    addWorkflow,
    removeWorkflow,
  ]);

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
      selectedLabel,
      labelOccurrences,
      switchTable,
      showInference,
    );
  }, [
    selectedLabel,
    labelOccurrences,
    switchTable,
    decodedTiff,
    imageCache,
    imageIndex,
    isWebcamActive,
    showInference,
  ]);

  useEffect(() => {
    if (
      !navigator ||
      !navigator.mediaDevices ||
      typeof navigator.mediaDevices.enumerateDevices !== "function"
    ) {
      return;
    }
    // retrieves the available devices and sets the active device to the first available device
    const updateDevices = async (): Promise<any> => {
      try {
        const availableDevices =
          await navigator.mediaDevices.enumerateDevices();
        const videoDevices = availableDevices.filter(
          (i) => i.kind === "videoinput",
        );
        setDevices(videoDevices);

        if (activeDeviceId === "" || activeDeviceId === undefined) {
          setActiveDeviceId(videoDevices[0].deviceId);
        }
      } catch (error) {
        alert(error);
      }
    };

    updateDevices().catch((error) => {
      alert(error);
    });
    const handleDeviceChange = (): void => {
      updateDevices().catch((error) => {
        alert(error);
      });
    };
    navigator.mediaDevices.addEventListener("devicechange", handleDeviceChange);
    return () => {
      navigator.mediaDevices.removeEventListener(
        "devicechange",
        handleDeviceChange,
      );
    };
  }, [activeDeviceId]);

  // Clear queue manager on unmount
  useEffect(() => {
    const manager = queueManagerRef.current;
    return () => {
      manager.clear();
    };
  }, []);

  // Acquire and store access token when authenticated
  useEffect(() => {
    if (!isAuthenticated || inProgress !== InteractionStatus.None) {
      return;
    }

    const getToken = async () => {
      try {
        const token = await acquireAccessToken(msalInstance, [apiScopeClaim]);
        setAccessToken(token);
      } catch (error) {
        console.error("Failed to acquire access token:", error);
      }
    };

    getToken();
  }, [isAuthenticated, inProgress, msalInstance, apiScopeClaim]);

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
        alert("Error checking registration status, see console for details");
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
          });
        });
        setAzureStorageDir(directories);
      } catch (error) {
        console.error(error);
        alert("Error reading Azure storage directory, see console for details");
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
  ]);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }
    if (inProgress !== InteractionStatus.None) {
      return;
    }
    if (!backendUrl || process.env.REACT_APP_MODE === "test") {
      return;
    }

    const loadModelMetadata = async () => {
      try {
        const accessToken = await acquireAccessToken(msalInstance, [
          apiScopeClaim,
        ]);

        const metadata = await fetchModelMetadata({ backendUrl, accessToken });
        setMetadata(metadata);

        // Find the default model from the metadata
        const defaultModel = metadata.find((model) => model.default);
        if (defaultModel) {
          setSelectedModel(defaultModel.pipeline_id);
        }
      } catch (error) {
        console.error(error);
        alert("Error fetching model metadata, see console for details");
      }
    };

    loadModelMetadata();
  }, [backendUrl, msalInstance, apiScopeClaim, isAuthenticated, inProgress]);

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
        padding: "0px 1.5vw",
        position: "relative",
        marginTop: "6.5vh",
        marginBottom: "10vh",
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
      {batchUploadOpen && (
        <BatchUploadPopup
          setBatchUploadOpen={setBatchUploadOpen}
          backendUrl={backendUrl}
          uuid={uuid}
          containerName={uuid}
          apiScopeClaim={apiScopeClaim}
        />
      )}
      {delDirectoryOpen && (
        <DeleteDirectoryPopup
          setDelDirectoryOpen={setDelDirectoryOpen}
          curDir={curDir}
          setCurDir={setCurDir}
          setReadAzureStorage={setReadAzureStorage}
          apiScopeClaim={apiScopeClaim}
        />
      )}
      {createDirectoryOpen && (
        <CreateDirectoryPopup
          setCreateDirectoryOpen={setCreateDirectoryOpen}
          curDir={curDir}
          setCurDir={setCurDir}
          setReadAzureStorage={setReadAzureStorage}
          apiScopeClaim={apiScopeClaim}
        />
      )}
      {saveOpen && (
        <SaveCapturePopup
          setSaveOpen={setSaveOpen}
          imageFormat={imageFormat}
          imageLabel={imageLabel}
          setImageFormat={setImageFormat}
          setImageLabel={setImageLabel}
          setSaveIndividualImage={setSaveIndividualImage}
          saveIndividualImage={saveIndividualImage}
        />
      )}
      {uploadOpen && (
        <UploadPopup
          setUploadOpen={setUploadOpen}
          pushImageToCache={pushImageToCache}
        />
      )}
      {modelInfoPopupOpen && (
        <ModelPopup
          setSwitchModelOpen={setModelInfoPopupOpen}
          switchModelOpen={modelInfoPopupOpen}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          realData={metadata}
        />
      )}
      {switchDeviceOpen && (
        <SwitchDevicePopup
          setSwitchDeviceOpen={setSwitchDeviceOpen}
          devices={devices}
          setDeviceId={setActiveDeviceId}
          activeDeviceId={activeDeviceId}
        />
      )}
      {deviceInfoOpen && (
        <DeviceInfoPopup
          setDeviceInfoOpen={setDeviceInfoOpen}
          deviceInfoOpen={deviceInfoOpen}
          devicesData={devicesData}
        />
      )}
      {props.creativeCommonsPopupOpen && (
        <CreativeCommonsPopup
          setCreativeCommonsPopupOpen={props.setCreativeCommonsPopupOpen}
          handleCreativeCommonsAgreement={props.handleCreativeCommonsAgreement}
        />
      )}

      <Box
        sx={{
          background: colours.CFIA_Background_White,
          color: colours.CFIA_Font_Black,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          width: "100%",
          maxWidth: "100%",
          minHeight: "100%",
        }}
      >
        <Box
          sx={{
            background: colours.CFIA_Background_White,
            color: colours.CFIA_Font_Black,
            display: "flex",
            flexDirection: "row",
            justifyContent: "center",
            alignItems: "center",
            minWidth: "100%",
            maxWidth: "100%",
            minHeight: "100%",
            position: "relative",
            zIndex: 0,
            padding: "0px 0px 0px 0px",
          }}
        >
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              width: "60%",
              maxWidth: "60%",
              minHeight: "100%",
              zIndex: 0,
              position: "relative",
            }}
          >
            <MicroscopeFeed
              capture={captureFeed}
              webcamRef={webcamRef}
              windowSize={props.windowSize}
              activeDeviceId={activeDeviceId}
              devices={devices}
              setSwitchDeviceOpen={setSwitchDeviceOpen}
              setDeviceInfoOpen={setDeviceInfoOpen}
              isLoading={isLoading}
              canvasRef={canvasRef}
              setSaveOpen={setSaveOpen}
              handleInference={handleInferenceRequest}
              handleDirectInference={handleDirectInference}
              setSwitchModelOpen={setModelInfoPopupOpen}
              selectedModel={selectedModel}
              metadata={metadata}
              setBatchUploadOpen={setBatchUploadOpen}
              setUploadOpen={setUploadOpen}
              isWebcamActive={isWebcamActive}
              onCaptureClick={() => {
                setIsWebcamActive(!isWebcamActive);
              }}
              toggleShowInference={(state: boolean) => setShowInference(state)}
              backendUrl={backendUrl}
              uuid={uuid}
              apiScopeClaim={apiScopeClaim}
            />
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "start",
              justifyContent: "start",
              width: "19%",
              maxWidth: "19%",
              height: "100%",
              maxHeight: "100%",
              zIndex: 0,
              position: "relative",
            }}
          >
            <StorageDirectory
              azureStorageDir={azureStorageDir}
              curDir={curDir}
              handleDirChange={handleDirChange}
              setCreateDirectoryOpen={setCreateDirectoryOpen}
              setDelDirectoryOpen={setDelDirectoryOpen}
              setCurDir={setCurDir}
            />
            <ImageCache />
            <ClassificationResults
              imageSrc={imageSrc}
              windowSize={props.windowSize}
              selectedLabel={selectedLabel}
              setSelectedLabel={setSelectedLabel}
              labelOccurrences={labelOccurrences}
              switchTable={switchTable}
              setSwitchTable={setSwitchTable}
              modelDisplayName={modelDisplayName}
            />
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default Body;
