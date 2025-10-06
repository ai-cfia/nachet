import React, { useState } from "react";
import {
  Box,
  Dialog,
  DialogContent,
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
    <Dialog
      open={true}
      onClose={handleClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 1,
            padding: "1vh",
          },
        },
      }}
    >
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "2vh",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                fontWeight: 600,
                fontSize: "1.8vh",
                color: colours.CFIA_Font_Black,
              }}
            >
              Choose Media Device
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              paddingLeft: "1vw",
              paddingRight: "1vw",
              marginTop: "1vh",
              marginBottom: "2vh",
            }}
          >
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
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default SwitchDevice;
