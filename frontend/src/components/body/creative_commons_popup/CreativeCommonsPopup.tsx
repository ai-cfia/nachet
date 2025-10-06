import React from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Button,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";

interface params {
  setCreativeCommonsPopupOpen: React.Dispatch<React.SetStateAction<boolean>>;
  handleCreativeCommonsAgreement: (agree: boolean) => void;
}

const CreativeCommonsPopup: React.FC<params> = (props) => {
  const introduction = `
By uploading your images to Seed Classification Interface, you agree to license your work under a Creative Commons Attribution-ShareAlike (CC BY-SA) License. This agreement outlines the terms and conditions of the license and other considerations.`;
  const termsAndConditions = `
Attribution: You allow others to copy, distribute, display, and perform your copyrighted work—and derivative works based upon it—but only if they give you the proper credit by citing your name and the source.
Share Alike: You allow others to distribute derivative works only under a license identical to the license that governs your work.
Machine Learning: You grant the CFIA the right to use your images to train machine learning models. These models may be used for various purposes, including research, analysis, and commercial activities.
Warranty: You represent and warrant that you are the legal owner of the content you are uploading and that it does not infringe on any copyright, trademark, or other rights of third parties.
Consent: If your image includes identifiable individuals, you affirm that you have obtained their consent for the image to be shared and used under these terms.
Waiver: The image is provided "as-is." You waive all warranties, including any regarding the image's accuracy or fitness for a particular purpose.`;
  const acknowledgment = `
By clicking "I Agree," you confirm that you have read and understood this agreement, and you will be legally bound by its terms and conditions.`;
  const handleClose = (): void => {
    props.setCreativeCommonsPopupOpen(false);
  };

  return (
    <Dialog
      open={true}
      onClose={handleClose}
      maxWidth="sm"
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
              marginBottom: "1vh",
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
              Use of Creative Commons Images
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              overflowY: "auto",
              maxHeight: "50vh",
              paddingTop: "1vh",
              paddingBottom: "0.5vh",
              paddingLeft: "1vw",
              paddingRight: "1vw",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                fontSize: "1.5vh",
                fontWeight: 600,
                color: colours.CFIA_Font_Black,
                marginBottom: "0.5vh",
                marginTop: "0.5vh",
              }}
            >
              Introduction
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontSize: "1.3vh",
                fontWeight: 500,
                color: colours.CFIA_Font_Black,
                textAlign: "left",
                marginBottom: "1vh",
              }}
            >
              {introduction.trim().replace(/\n/g, " ")}
            </Typography>
            <Typography
              variant="h6"
              sx={{
                fontSize: "1.5vh",
                fontWeight: 600,
                color: colours.CFIA_Font_Black,
                marginBottom: "0.5vh",
                marginTop: "0.5vh",
              }}
            >
              Terms and Conditions
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontSize: "1.3vh",
                fontWeight: 500,
                color: colours.CFIA_Font_Black,
                textAlign: "left",
                marginBottom: "1vh",
              }}
            >
              {termsAndConditions.trim().replace(/\n/g, " ")}
            </Typography>
            <Typography
              variant="h6"
              sx={{
                fontSize: "1.5vh",
                fontWeight: 600,
                color: colours.CFIA_Font_Black,
                marginBottom: "0.5vh",
                marginTop: "0.5vh",
              }}
            >
              Acknowledgement
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontSize: "1.3vh",
                fontWeight: 500,
                color: colours.CFIA_Font_Black,
                textAlign: "left",
                marginBottom: "1vh",
              }}
            >
              {acknowledgment.trim().replace(/\n/g, " ")}
            </Typography>
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              marginTop: "2vh",
              marginBottom: "1vh",
              gap: "2vh",
            }}
          >
            <Button
              variant="outlined"
              size="medium"
              sx={{
                borderRadius: "0.4vh",
                paddingTop: "0.6vh",
                paddingBottom: "0.6vh",
                paddingLeft: "1.5vh",
                paddingRight: "1.5vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                color: colours.CFIA_Background_Blue,
                "&:hover": {
                  backgroundColor: colours.CFIA_Background_Blue,
                  color: colours.CFIA_Background_White,
                  border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                  transition: "0.2s ease-in-out all",
                },
              }}
              onClick={() => {
                props.handleCreativeCommonsAgreement(true);
              }}
            >
              I Agree
            </Button>
            <Button
              variant="outlined"
              size="medium"
              sx={{
                borderRadius: "0.4vh",
                paddingTop: "0.6vh",
                paddingBottom: "0.6vh",
                paddingLeft: "1.5vh",
                paddingRight: "1.5vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.15vh solid LightGrey`,
                color: colours.CFIA_Font_Black,
                "&:hover": {
                  backgroundColor: "#F5F5F5",
                  transition: "0.2s ease-in-out all",
                  border: `0.15vh solid LightGrey`,
                },
              }}
              onClick={() => {
                props.handleCreativeCommonsAgreement(false);
              }}
            >
              I Disagree
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default CreativeCommonsPopup;
