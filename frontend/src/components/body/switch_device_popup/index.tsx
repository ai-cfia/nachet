import React, { useState } from "react";
import { Overlay, InfoContainer } from "./indexElements";
import {
  Box,
  CardHeader,
  IconButton,
  Select,
  MenuItem,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { deviceIdSchema } from "@common/validation";

interface params {
  setSwitchDeviceOpen: React.Dispatch<React.SetStateAction<boolean>>;
  devices: MediaDeviceInfo[];
  setDeviceId: React.Dispatch<React.SetStateAction<string | undefined>>;
  activeDeviceId: string | undefined;
}

const SwitchDevice: React.FC<params> = (props) => {
  const [deviceError, setDeviceError] = useState<string>("");

  const handleClose = (): void => {
    props.setSwitchDeviceOpen(false);
    setDeviceError("");
  };

  const handleSwitch = (event: SelectChangeEvent): void => {
    const selectedDeviceId = event.target.value;

    // Validate device ID
    const validation = deviceIdSchema.safeParse(selectedDeviceId);
    if (!validation.success) {
      setDeviceError(validation.error.issues[0].message);
      return;
    }

    // Clear error and proceed
    setDeviceError("");
    if (props.setDeviceId === undefined) {
      return;
    }
    props.setDeviceId(selectedDeviceId);
    props.setSwitchDeviceOpen(false);
  };

  return (
    <Overlay>
      <Box
        sx={{
          width: "20vw",
          height: "fit-content",
          zIndex: 30,
          border: `0.01vh solid LightGrey`,
          borderRadius: 1,
          background: colours.CFIA_Background_White,
        }}
        boxShadow={1}
      >
        <CardHeader
          title="Choose Media Device"
          titleTypographyProps={{
            variant: "h6",
            align: "left",
            fontWeight: 600,
            fontSize: "1.3vh",
            color: colours.CFIA_Font_Black,
            zIndex: 30,
          }}
          action={
            <IconButton onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          }
          sx={{ padding: "0.8vh 0.8vh 0.8vh 0.8vh" }}
        />
        <InfoContainer>
          <Select
            value={props.activeDeviceId}
            onChange={handleSwitch}
            sx={{ fontSize: "1.2vh" }}
            size="small"
            fullWidth
          >
            {props.devices.map((device) => (
              <MenuItem
                key={device.deviceId}
                value={device.deviceId}
                sx={{ fontSize: "1.2vh" }}
              >
                {device.label.split("(")[0]}
              </MenuItem>
            ))}
          </Select>
          {deviceError && (
            <Typography
              color="error"
              variant="caption"
              sx={{ marginTop: "0.5vh" }}
            >
              {deviceError}
            </Typography>
          )}
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default SwitchDevice;
