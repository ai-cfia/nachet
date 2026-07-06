// \components\body\microscope_feed\MicroscopeFeedControlsView.tsx
// Controls for MicroscopeFeed component
import { useMemo } from "react";
import { Box, Button, Switch, Badge } from "@mui/material";
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
import NotificationsIcon from "@mui/icons-material/Notifications";
import { colours } from "@styles/colours";
import { useDeviceStore } from "@stores/useDeviceStore";
import { useImageStore } from "@stores/useImageStore";
import { useModalStore } from "@stores/useModalStore";
import { useWebcamStore } from "@stores/useWebcamStore";
import { useModelStore } from "@stores/useModelStore";
import { useNotificationStore } from "@stores/useNotificationStore";
import { useNachetAuth } from "@auth";

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
  const { getMissingMetadataCount } = useDeviceStore();
  const { images: imageCache } = useImageStore();
  const { selectedModel, metadata } = useModelStore();
  const { activeAccount } = useNachetAuth();

  // Modal store actions
  const {
    openSwitchDevicePopup,
    openSampleMetadataPopup,
    openUploadPopup,
    openModelInfoPopup,
    openSavePopup,
    openBatchUploadPopup,
    openNotificationLog,
  } = useModalStore();

  // Notification store
  const { getUnreadErrorCount, markAllErrorsAsRead } = useNotificationStore();

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

  const isGuest = activeAccount?.isGuest ?? true;

  // Find the model name from metadata based on selectedModel (pipelineId)
  const selectedModelName = useMemo(() => {
    const model = metadata.find((m) => m.pipelineId === selectedModel);
    return model?.modelName || selectedModel;
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
        justifyContent: "flex-start",
        flexWrap: "wrap",
        alignItems: "center",
        padding: "0.8vh",
        rowGap: "0.8vh",
        columnGap: "0.4vh",
      }}
    >
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.notificationsLabel")}
        icon={
          <Badge badgeContent={getUnreadErrorCount()} color="error">
            <NotificationsIcon color="inherit" style={iconStyle} />
          </Badge>
        }
        disabled={false} // always active
        onClick={() => {
          openNotificationLog();
          markAllErrorsAsRead();
        }}
        sx={{ marginRight: "0.2vh" }}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.deviceLabel")}
        icon={
          <Badge badgeContent={getMissingMetadataCount()} color="error">
            <InfoIcon color="inherit" style={iconStyle} />
          </Badge>
        }
        disabled={false} // Always active
        onClick={openSampleMetadataPopup}
      />
      <ButtonMicroscopeFeed
        label={deviceLabel.slice(0, 8)} // Limit label length to 8 characters
        icon={<SwitchCameraIcon color="inherit" style={iconStyle} />}
        endIcon={<ArrowDropDownIcon color="inherit" />}
        disabled={!isWebcamActive || getMissingMetadataCount() > 0} // Disable when the webcam is active
        onClick={openSwitchDevicePopup}
      />
      <ButtonMicroscopeFeed
        label={t("microscopeFeed.controls.captureLabel")}
        icon={<AddAPhotoIcon color="inherit" style={iconStyle} />}
        disabled={!isWebcamActive || getMissingMetadataCount() > 0} // Disable when the webcam is inactive or device info is not set
        onClick={() => {
          capture();
        }}
      />
      <Switch
        checked={!isWebcamActive}
        disabled={getMissingMetadataCount() > 0} // Disable when device info is not set
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
