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
import { useTranslation } from "react-i18next";

interface params {
  setCreativeCommonsPopupOpen: React.Dispatch<React.SetStateAction<boolean>>;
  handleCreativeCommonsAgreement: (agree: boolean) => void;
}

const CreativeCommonsPopup: React.FC<params> = (props) => {
  const { t } = useTranslation("popups");

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
              {t("creativeCommons.title")}
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
              {t("creativeCommons.introduction.heading")}
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
              {t("creativeCommons.introduction.text")}
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
              {t("creativeCommons.termsAndConditions.heading")}
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
              {t("creativeCommons.termsAndConditions.attribution")}{" "}
              {t("creativeCommons.termsAndConditions.shareAlike")}{" "}
              {t("creativeCommons.termsAndConditions.machineLearning")}{" "}
              {t("creativeCommons.termsAndConditions.warranty")}{" "}
              {t("creativeCommons.termsAndConditions.consent")}{" "}
              {t("creativeCommons.termsAndConditions.waiver")}
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
              {t("creativeCommons.acknowledgment.heading")}
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
              {t("creativeCommons.acknowledgment.text")}
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
              {t("creativeCommons.agreeButton")}
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
              {t("creativeCommons.disagreeButton")}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default CreativeCommonsPopup;
