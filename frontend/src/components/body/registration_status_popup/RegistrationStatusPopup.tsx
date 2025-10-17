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
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { colours } from "../../../styles/colours";

interface params {
  userOid: string;
  setPopupOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

const RegistrationStatusPopup: React.FC<params> = (props) => {
  const { userOid, setPopupOpen } = props;
  const [copied, setCopied] = React.useState(false);

  const handleClose = (): void => {
    setPopupOpen(false);
  };

  const handleCopyOid = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(userOid);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy OID:", err);
    }
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
              Account Registration Required
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              paddingTop: "1vh",
              paddingBottom: "0.5vh",
              paddingLeft: "1vw",
              paddingRight: "1vw",
            }}
          >
            <Typography
              variant="body2"
              sx={{
                fontSize: "1.4vh",
                fontWeight: 500,
                color: colours.CFIA_Font_Black,
                textAlign: "left",
                marginBottom: "1.5vh",
              }}
            >
              Your account is not yet registered in the system. Please contact
              your system administrator to request access.
            </Typography>
            <Typography
              variant="body2"
              sx={{
                fontSize: "1.4vh",
                fontWeight: 500,
                color: colours.CFIA_Font_Black,
                textAlign: "left",
                marginBottom: "0.5vh",
              }}
            >
              Provide the following user ID to your administrator:
            </Typography>
            <Box
              sx={{
                display: "flex",
                flexDirection: "row",
                alignItems: "center",
                backgroundColor: "#F5F5F5",
                padding: "1vh",
                borderRadius: "0.4vh",
                marginBottom: "1.5vh",
                gap: "1vh",
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  fontSize: "1.3vh",
                  fontFamily: "monospace",
                  color: colours.CFIA_Font_Black,
                  wordBreak: "break-all",
                  flex: 1,
                }}
              >
                {userOid}
              </Typography>
              <IconButton
                onClick={handleCopyOid}
                size="small"
                sx={{
                  padding: "0.5vh",
                  "&:hover": {
                    backgroundColor: "#E0E0E0",
                  },
                }}
                title="Copy to clipboard"
              >
                <ContentCopyIcon sx={{ fontSize: "1.5vh" }} />
              </IconButton>
            </Box>
            {copied && (
              <Typography
                variant="caption"
                sx={{
                  fontSize: "1.2vh",
                  color: colours.CFIA_Background_Blue,
                  textAlign: "center",
                  marginTop: "-1vh",
                  marginBottom: "1vh",
                }}
              >
                Copied to clipboard!
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              marginTop: "1vh",
              marginBottom: "1vh",
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
              onClick={handleClose}
            >
              Close
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default RegistrationStatusPopup;
