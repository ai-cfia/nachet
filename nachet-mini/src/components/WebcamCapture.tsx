import Webcam from "react-webcam";
import { Box, Typography } from "@mui/material";
import { useWebcamDevices } from "@hooks/useWebcamDevices";

interface Props {
  webcamRef: React.RefObject<Webcam | null>;
  onUserMediaError: (err: string | DOMException) => void;
}

const WebcamCapture = ({ webcamRef, onUserMediaError }: Props) => {
  const { devices, activeDeviceId } = useWebcamDevices();

  return (
    <Box
      sx={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        bgcolor: "#000",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        border: "0.01vh solid LightGrey",
        borderRadius: "0.4vh",
      }}
    >
      {devices.length > 0 ? (
        <Webcam
          key={activeDeviceId}
          ref={webcamRef}
          mirrored={false}
          width="100%"
          height="100%"
          style={{ objectFit: "contain", display: "block" }}
          videoConstraints={{
            width: 1920,
            height: 1080,
            deviceId: activeDeviceId ? { exact: activeDeviceId } : undefined,
          }}
          screenshotFormat="image/png"
          screenshotQuality={1}
          onUserMediaError={onUserMediaError}
        />
      ) : (
        <Typography color="grey.500" sx={{ fontSize: "1.3vh" }}>
          No camera detected
        </Typography>
      )}
    </Box>
  );
};

export default WebcamCapture;
