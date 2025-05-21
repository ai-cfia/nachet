import React from "react";
import { Overlay, InfoContainer } from "./indexElements";
import { Box, CardHeader, IconButton, Input } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";

interface params {
  setUploadOpen: React.Dispatch<React.SetStateAction<boolean>>;
  pushImageToCache: (imageUrl: string) => void;
}

const UploadPopup: React.FC<params> = (props): JSX.Element => {
  const { setUploadOpen, pushImageToCache } = props;

  const uploadImage = (event: any): void => {
    // loads image from local storage to cache when upload button is pressed
    event.preventDefault();
    const file = event.target.files[0];
    if (file !== undefined) {
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
          title="Load Image"
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
          <Input
            type="file"
            fullWidth
            onChange={uploadImage}
            sx={{
              fontSize: "0.7vw",
            }}
          />
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default UploadPopup;
