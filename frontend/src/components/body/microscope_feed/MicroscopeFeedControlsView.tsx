// \components\body\microscope_feed\MicroscopeFeedControlsView.tsx
// Controls for MicroscopeFeed component
import { useMemo } from "react";
import { Box, Button, Switch } from "@mui/material";
import { useTranslation } from "react-i18next";
// Import icons
import SwitchCameraIcon from "@mui/icons-material/SwitchCamera";
import AddAPhotoIcon from "@mui/icons-material/AddAPhoto";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DownloadIcon from "@mui/icons-material/Download";
import CropFreeIcon from "@mui/icons-material/CropFree";
import DonutSmallIcon from "@mui/icons-material/DonutSmall";
import InfoIcon from "@mui/icons-material/Info";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import { colours } from "@styles/colours";
import { useAccount } from "@azure/msal-react";
import { useDeviceStore } from "@stores/useDeviceStore";
import { useImageStore } from "@stores/useImageStore";
import { useModalStore } from "@stores/useModalStore";
import { useWebcamStore } from "@stores/useWebcamStore";
import { useModelStore } from "@stores/useModelStore";

export interface MicroscopeFeedControlsViewProps {
  isWebcamActive: boolean;
  capture: () => void;
  onCaptureClick: () => void;
  handleInference: () => void;
  handleDirectInference: () => void;
}

const ButtonMicroscopeFeed = (props: {
  label: string;
  icon: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
  endIcon?: React.ReactNode;
  sx?: object;
}) => {
  const { label, icon, onClick, disabled, endIcon, sx } = props;
  const buttonStyle = {
    borderRadius: "0.4vh",
    paddingTop: "0.3vh",
    paddingBottom: "0.3vh",
    paddingLeft: "0.7vh",
    paddingRight: "0.7vh",
    fontSize: "1.17vh",
    width: "fit-content",
    border: `0.01vh solid LightGrey`,
    "&:hover": {
      backgroundColor: "#F5F5F5",
      transition: "0.1s ease-in-out all",
    },
    ...sx,
  };
  return (
    <Button
      color="inherit"
      variant="outlined"
      disabled={disabled}
      onClick={onClick}
      sx={buttonStyle}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        {icon}
        <span>{label}</span>
        {endIcon}
      </div>
    </Button>
  );
};

export const MicroscopeFeedControlsView = (
  props: MicroscopeFeedControlsViewProps,
) => {
  const {
    isWebcamActive,
    capture,
    onCaptureClick,
    handleInference,
    handleDirectInference,
  } = props;

  const { t } = useTranslation("main");

  const { devices, activeDeviceId } = useWebcamStore();
  const { isDeviceInfoSet } = useDeviceStore();
  const { images: imageCache } = useImageStore();
  const { selectedModel, metadata } = useModelStore();
  const accountInfo = useAccount();

  // Modal store actions
  const {
    openSwitchDevicePopup,
    openDeviceInfoPopup,
    openUploadPopup,
    openModelInfoPopup,
    openSavePopup,
    openBatchUploadPopup,
  } = useModalStore();

  // Icon styles
  const iconStyle = {
    fontSize: "1.7vh",
    paddingRight: "0.4vh",
    marginTop: 0,
    marginBottom: 0,
    marginRight: 0,
    marginLeft: 0,
    paddingTop: 0,
    paddingBottom: 0,
    paddingLeft: 0,
  };

  const endIconStyle = {
    fontSize: "1.7vh",
    margin: 0,
    padding: 0,
  };

  // Derive isGuest from accountInfo
  // acct === 0 means member account, acct !== 0 or undefined means guest account
  // Defensive: treat missing/undefined acct as guest (hide D button)
  const isGuest = useMemo(() => {
    const idTokenClaims = accountInfo?.idTokenClaims as
      | { acct?: number }
      | undefined;
    const acctClaim = idTokenClaims?.acct;

    // Only acct === 0 means member (show D button)
    // Everything else (undefined, null, non-zero) means guest (hide D button)
    return acctClaim !== 0;
  }, [accountInfo]);

  // Find the model name from metadata based on selectedModel (pipeline_id)
  const selectedModelName = useMemo(() => {
    const model = metadata.find((m) => m.pipeline_id === selectedModel);
    return model?.model_name || selectedModel;
  }, [metadata, selectedModel]);

  // Get device label
  const activeDevice = devices.find(
    (device) => device.deviceId === activeDeviceId,
  );
  const deviceLabel = activeDevice?.label || "SWITCH";

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "row",
        justifyContent: "center",
        flexWrap: "wrap",
        alignItems: "center",
        padding: "0.8vh",
        rowGap: "0.8vh",
        columnGap: "0.4vh",
      }}
    >
      <ButtonMicroscopeFeed
        label={deviceLabel.slice(0, 8)} // Limit label length to 8 characters
        icon={<SwitchCameraIcon color="inherit" style={iconStyle} />}
        endIcon={<ArrowDropDownIcon color="inherit" />}
        disabled={!isWebcamActive} // Disable when the webcam is active
        onClick={openSwitchDevicePopup}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.deviceLabel")}
        icon={<InfoIcon color="inherit" style={iconStyle} />}
        disabled={false} // Always active
        onClick={openDeviceInfoPopup}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.captureLabel")}
        icon={<AddAPhotoIcon color="inherit" style={iconStyle} />}
        disabled={!isWebcamActive || !isDeviceInfoSet()} // Disable when the webcam is inactive or device info is not set
        onClick={() => {
          capture();
        }}
      />
      <Switch
        checked={!isWebcamActive}
        onChange={onCaptureClick}
        size="small"
        sx={{
          "& .MuiSwitch-switchBase": {
            color: colours.CFIA_Background_Blue,
          },
          "& .MuiSwitch-track": {
            backgroundColor: colours.CFIA_Background_Blue,
          },
        }}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.loadLabel")}
        icon={<UploadFileIcon color="inherit" style={iconStyle} />}
        disabled={isWebcamActive} // Disable when the webcam is active
        onClick={openUploadPopup}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.saveLabel")}
        icon={<DownloadIcon color="inherit" style={iconStyle} />}
        disabled={isWebcamActive} // Disable when the webcam is active
        onClick={openSavePopup}
        sx={{ marginRight: "0.2vh" }}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.batchLabel")}
        icon={<UploadFileIcon color="inherit" style={iconStyle} />}
        disabled={isWebcamActive} // Disable when the webcam is active
        onClick={openBatchUploadPopup}
        sx={{ marginRight: "0.2vh" }}
      />
      <ButtonMicroscopeFeed
        label={selectedModelName.slice(0, 10)}
        icon={<DonutSmallIcon color="inherit" style={iconStyle} />}
        disabled={isWebcamActive} // Disable when the webcam is active
        onClick={openModelInfoPopup}
        endIcon={<ArrowDropDownIcon color="inherit" style={endIconStyle} />}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.classifyLabel")}
        icon={<CropFreeIcon color="inherit" style={iconStyle} />}
        disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
        onClick={() => {
          handleInference();
        }}
      />
      {!isGuest && (
        <ButtonMicroscopeFeed
          label={t("microscopeFeed.controls.directLabel")}
          icon={<CropFreeIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
          onClick={() => {
            handleDirectInference();
          }}
        />
      )}
      {/* <ButtonMicroscopeFeed
        label="ANNOTATE"
        icon={<FormatShapesOutlinedIcon color="inherit" style={iconStyle} />}
        disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
        onClick={() => {
          handleAnnotate();
        }}
      /> */}
    </Box>
  );
};
