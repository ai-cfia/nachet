import React from "react";
import { Overlay, InfoContainer, ButtonWrap, Text } from "./indexElements";
import { Box, CardHeader, IconButton, Button } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "@styles/colours";
import { useBackendUrl } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { deleteAzureStorageDir } from "@common/api";

interface params {
  setDelDirectoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  curDir: string;
  setCurDir: React.Dispatch<React.SetStateAction<string>>;
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
  apiScopeClaim: string;
}

const DeleteDirectoryPopup: React.FC<params> = (props) => {
  const {
    apiScopeClaim,
    setDelDirectoryOpen,
    curDir,
    setCurDir,
    setReadAzureStorage,
  } = props;
  const backendURL = useBackendUrl();
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const handleDelFromDirectory = (): void => {
    if (!isAuthenticated) {
      alert("You must be signed in to delete a directory");
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
      return;
    }

    acquireAccessToken(msalInstance, [apiScopeClaim])
      .then((accessToken) => {
        // makes a post request to the backend to delete a directory in azure storage
        return deleteAzureStorageDir({
          backendUrl: backendURL,
          folderName: curDir,
          accessToken,
        });
      })
      .then(() => {
        setCurDir("General");
        setReadAzureStorage((prev) => !prev);
      })
      .catch((error) => {
        alert("Error deleting directory, see console for more details");
        console.error(error);
      });
  };

  const handleClose = (): void => {
    setDelDirectoryOpen(false);
  };
  const handleYes = (): void => {
    handleDelFromDirectory();
    setDelDirectoryOpen(false);
  };

  return (
    <Overlay>
      <Box
        sx={{
          width: "15vw",
          height: "20vh",
          zIndex: 30,
          border: `0.01vh solid LightGrey`,
          borderRadius: 1,
          background: colours.CFIA_Background_White,
        }}
        boxShadow={1}
      >
        <CardHeader
          title="Delete Directory"
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
          <Text>Are you sure you want to delete {curDir}?</Text>
          <ButtonWrap>
            <Button
              variant="outlined"
              size="medium"
              sx={{
                marginLeft: 0,
                borderRadius: "0.4vh",
                paddingTop: "0.3vh",
                paddingBottom: "0.3vh",
                paddingLeft: "0.7vh",
                paddingRight: "0.7vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.01vh solid LightGrey`,
                color: colours.CFIA_Font_Black,
                "&:hover": {
                  backgroundColor: "#F5F5F5",
                  transition: "0.1s ease-in-out all",
                  border: `0.01vh solid LightGrey`,
                },
                marginRight: "2vw",
              }}
              onClick={handleYes}
            >
              Delete
            </Button>
            <Button
              variant="outlined"
              size="medium"
              sx={{
                marginLeft: 0,
                borderRadius: "0.4vh",
                paddingTop: "0.3vh",
                paddingBottom: "0.3vh",
                paddingLeft: "0.7vh",
                paddingRight: "0.7vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.01vh solid LightGrey`,
                color: colours.CFIA_Font_Black,
                "&:hover": {
                  backgroundColor: "#F5F5F5",
                  transition: "0.1s ease-in-out all",
                  border: `0.01vh solid LightGrey`,
                },
              }}
              onClick={handleClose}
            >
              Cancel
            </Button>
          </ButtonWrap>
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default DeleteDirectoryPopup;
