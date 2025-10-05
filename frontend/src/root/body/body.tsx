// root\body\index.tsx
import { useState, useRef, useEffect, useMemo } from "react";
import type Webcam from "react-webcam";
import { BodyContainer } from "./indexElements";
import Classifier from "../../pages/classifier";
import SavePopup from "../../components/body/save_capture_popup";
import UploadPopup from "../../components/body/load_image_popup";
import ModelInfoPopup from "../../components/body/model_popup";
import SwitchDevice from "../../components/body/switch_device_popup";
import {
  CreateDirectoryPopup,
  BatchUploadPopup,
  DeleteDirectoryPopup,
  AuthPopup,
} from "@components/body";
import CreativeCommonsPopup from "../../components/body/creative_commons_popup";
import { useBackendUrl, useDecoderTiff } from "@hooks";
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
  loadCaptureToCache,
  loadResultsToCache,
  loadToCanvas,
  nextCacheIndex,
  fetchModelMetadata,
  inferenceRequest,
  readAzureStorageDir,
  // requestUUID,
} from "@common";
import {
  AzureStorageDirectoryItem,
  AzureStorageDirectoryItemApi,
  Images,
  LabelOccurrences,
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
  const [imageSrc, setImageSrc] = useState<string>(defaultImageSrc);
  const [imageTiff, setImageTiff] = useState<string>("");
  const [imageIndex, setImageIndex] = useState<number>(0);
  const [imageFormat, setImageFormat] = useState<string>("image/png");
  const [imageLabel, setImageLabel] = useState<string>("");
  const [saveOpen, setSaveOpen] = useState(false);
  const [batchUploadOpen, setBatchUploadOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [modelInfoPopupOpen, setModelInfoPopupOpen] = useState(false);
  const [switchDeviceOpen, setSwitchDeviceOpen] = useState(false);
  const [createDirectoryOpen, setCreateDirectoryOpen] = useState(false);
  const [imageCache, setImageCache] = useState<Images[]>([]);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [activeDeviceId, setActiveDeviceId] = useState<string | undefined>(
    undefined,
  );
  const [curDir, setCurDir] = useState<string>("General");
  const [readAzureStorage, setReadAzureStorage] = useState<boolean>(false);
  const [azureStorageDir, setAzureStorageDir] = useState<
    AzureStorageDirectoryItem[]
  >([]);
  const [delDirectoryOpen, setDelDirectoryOpen] = useState<boolean>(false);
  const [selectedModel, setSelectedModel] = useState("Swin transformer");
  const [modelDisplayName, setModelDisplayName] = useState("");
  const [selectedLabel, setSelectedLabel] = useState<string>("all");
  const [labelOccurrences, setLabelOccurrences] = useState<LabelOccurrences>(
    {},
  );
  const [saveIndividualImage, setSaveIndividualImage] = useState<string>("0");
  const [switchTable, setSwitchTable] = useState<boolean>(true);
  const webcamRef = useRef<Webcam>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [isWebcamActive, setIsWebcamActive] = useState(true); // This state determines the visibility of the webcam
  const [isLoading, setIsLoading] = useState(false);
  const [metadata, setMetadata] = useState<ModelMetadata[]>([]);
  const [showInference, setShowInference] = useState<boolean>(true);
  const [authPopupOpen, setAuthPopupOpen] = useState<boolean>(false);
  const decodedTiff = useDecoderTiff(imageTiff);
  const backendUrl = useBackendUrl();
  const apiScopeClaim = props.apiScopeClaim;
  const { instance: msalInstance, inProgress, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const accountInfo = useAccount();
  const uuid = accountInfo?.idTokenClaims?.oid ?? "";

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
    pushImageToCache(src);
  };

  const pushImageToCache = (src: string): void => {
    // loads image to cache when image is uploaded
    const nextIndex = nextCacheIndex(imageIndex, imageCache);
    loadCaptureToCache(src, imageCache, nextIndex).then((newCache) => {
      setImageCache(newCache);
      setImageIndex(nextIndex);
    });
  };

  const removeFromCache = (index: number): void => {
    // removes image from cache based on given index value when delete button is pressed
    const newCache = imageCache.filter((item) => item.index !== index);
    setImageCache(newCache);
    setImageIndex(nextCacheIndex(imageIndex, newCache));
  };

  const clearCache = (): void => {
    // clears image cache when clear button is pressed
    setImageCache([]);
    setImageIndex(0);
  };

  const handleDirChange = (dir: string): void => {
    // sets the current directory for azure storage
    setCurDir(dir.replace(/\s/g, "-"));
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
    if (curDir !== "") {
      const imageObject = imageCache.find((item) => item.index === imageIndex);
      if (imageObject === undefined) {
        return;
      }
      setIsLoading(true);
      acquireAccessToken(msalInstance, [apiScopeClaim])
        .then((accessToken) => {
          return inferenceRequest({
            backendUrl,
            selectedModel,
            imageObject,
            curDir,
            accessToken,
            container_uuid: uuid,
          });
        })
        .then((response) => {
          setReadAzureStorage(!readAzureStorage);
          setImageCache(loadResultsToCache(response, imageCache, imageIndex));
          setModelDisplayName(selectedModel);
        })
        .catch((error) => {
          alert("Error fetching inference data, see console for details");
          console.error(error);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      alert("Please select a directory");
    }
  };

  useEffect(() => {
    const imageData = imageCache.find((img) => img.index === imageIndex);
    if (imageData === undefined) {
      setImageSrc(defaultImageSrc);
      return;
    }
    const labelOccurrences = getLabelOccurrence(imageData);
    setLabelOccurrences(labelOccurrences);
    setImageSrc(imageData.src);
    if (imageData.src.includes("image/tiff")) {
      setImageTiff(imageData.src);
    }
  }, [imageIndex, imageCache]);

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
  ]);

  const handleImageUpload = (): void => {
    // Set the logic for handling image upload and then:
    setIsWebcamActive(false); // Hide the webcam after the image is loaded
  };

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
          setSelectedModel(defaultModel.model_name);
        }
      } catch (error) {
        console.error(error);
        alert("Error fetching model metadata, see console for details");
      }
    };

    loadModelMetadata();
  }, [backendUrl, msalInstance, apiScopeClaim, isAuthenticated, inProgress]);

  // Auto-open auth popup when user is not authenticated
  useEffect(() => {
    if (!isAuthenticated && inProgress === InteractionStatus.None) {
      setAuthPopupOpen(true);
    }
  }, [isAuthenticated, inProgress]);

  // Auto-close auth popup when user becomes authenticated
  useEffect(() => {
    if (isAuthenticated && authPopupOpen) {
      setAuthPopupOpen(false);
    }
  }, [isAuthenticated, authPopupOpen]);

  return (
    <BodyContainer width={props.windowSize.width} data-testid="body-component">
      <AuthPopup
        open={authPopupOpen}
        onClose={() => setAuthPopupOpen(false)}
        apiScopeClaim={apiScopeClaim}
      />
      {saveOpen && (
        <SavePopup
          imageCache={imageCache}
          imageSrc={imageSrc}
          setSaveOpen={setSaveOpen}
          imageFormat={imageFormat}
          imageLabel={imageLabel}
          setImageFormat={setImageFormat}
          setImageLabel={setImageLabel}
          setSaveIndividualImage={setSaveIndividualImage}
          saveIndividualImage={saveIndividualImage}
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
      {uploadOpen && (
        <UploadPopup
          setUploadOpen={setUploadOpen}
          pushImageToCache={pushImageToCache}
        />
      )}
      {modelInfoPopupOpen && (
        <ModelInfoPopup
          setSwitchModelOpen={setModelInfoPopupOpen}
          switchModelOpen={modelInfoPopupOpen}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          realData={metadata}
        />
      )}
      {switchDeviceOpen && (
        <SwitchDevice
          setSwitchDeviceOpen={setSwitchDeviceOpen}
          devices={devices}
          setDeviceId={setActiveDeviceId}
          activeDeviceId={activeDeviceId}
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
          handeDirChange={handleDirChange}
          curDir={curDir}
          setCurDir={setCurDir}
          setReadAzureStorage={setReadAzureStorage}
          apiScopeClaim={apiScopeClaim}
        />
      )}
      {props.creativeCommonsPopupOpen && (
        <CreativeCommonsPopup
          setCreativeCommonsPopupOpen={props.setCreativeCommonsPopupOpen}
          handleCreativeCommonsAgreement={props.handleCreativeCommonsAgreement}
        />
      )}

      <Classifier
        handleInference={handleInferenceRequest}
        imageIndex={imageIndex}
        setBatchUploadOpen={setBatchUploadOpen}
        setUploadOpen={setUploadOpen}
        imageSrc={imageSrc}
        webcamRef={webcamRef}
        imageFormat={imageFormat}
        setSaveOpen={setSaveOpen}
        capture={captureFeed}
        savedImages={imageCache}
        setImageCache={setImageCache}
        clearImageCache={clearCache}
        canvasRef={canvasRef}
        removeImage={removeFromCache}
        setSwitchModelOpen={setModelInfoPopupOpen}
        setSwitchDeviceOpen={setSwitchDeviceOpen}
        windowSize={props.windowSize}
        activeDeviceId={activeDeviceId}
        azureStorageDir={azureStorageDir}
        curDir={curDir}
        setImageIndex={setImageIndex}
        handleDirChange={handleDirChange}
        setCreateDirectoryOpen={setCreateDirectoryOpen}
        setDelDirectoryOpen={setDelDirectoryOpen}
        selectedLabel={selectedLabel}
        setSelectedLabel={setSelectedLabel}
        labelOccurrences={labelOccurrences}
        switchTable={switchTable}
        setSwitchTable={setSwitchTable}
        setCurDir={setCurDir}
        isWebcamActive={isWebcamActive}
        onCaptureClick={() => {
          setIsWebcamActive(!isWebcamActive);
        }}
        onImageUpload={handleImageUpload}
        modelDisplayName={modelDisplayName}
        isLoading={isLoading}
        toggleShowInference={(state: boolean) => setShowInference(state)}
        backendUrl={backendUrl}
        uuid={uuid}
        apiScopeClaim={apiScopeClaim}
      />
    </BodyContainer>
  );
};

export default Body;
