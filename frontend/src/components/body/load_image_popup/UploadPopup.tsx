import React from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Input,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { validateImageFile } from "@common";

interface params {
  setUploadOpen: React.Dispatch<React.SetStateAction<boolean>>;
  pushImageToCache: (imageUrl: string) => void;
}

const UploadPopup: React.FC<params> = (props) => {
  const { setUploadOpen, pushImageToCache } = props;

  const uploadImage = async (event: any): Promise<void> => {
    // loads image from local storage to cache when upload button is pressed
    event.preventDefault();
    const file = event.target.files[0];

    if (file !== undefined) {
      // Validate the file with comprehensive checks including dimensions
      const validation = await validateImageFile(file);
      if (!validation.isValid) {
        alert(validation.errors.join("\n"));
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result !== "string") {
          return;
        }
        pushImageToCache(reader.result);
      };
      reader.readAsDataURL(file);
    }
    setUploadOpen(false);
  };

  const handleClose = (): void => {
    setUploadOpen(false);
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
              Load Image
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
            <Input
              type="file"
              fullWidth
              onChange={uploadImage}
              inputProps={{
                accept: "image/png",
              }}
              sx={{
                fontSize: "1.2vh",
              }}
            />
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default UploadPopup;
