import React from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Button,
  Radio,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import testData from "../../../static_data/static_model_data.json";

interface params {
  setSwitchModelOpen: React.Dispatch<React.SetStateAction<boolean>>;
  switchModelOpen: boolean;
  selectedModel: string;
  setSelectedModel: React.Dispatch<React.SetStateAction<string>>;
  realData: any[]; // Type should be adjusted to match the actual data structure
}

const SwitchModel: React.FC<params> = (props) => {
  const handleClose = (): void => {
    props.setSwitchModelOpen(false);
  };

  const selectModel = (model: string): void => {
    console.log("Model selected:", model);
    props.setSelectedModel(model);
  };

  const close = (): void => {
    handleClose(); // Call handleClose to close the popup
  };

  const dataToDisplay =
    process.env.VITE_APP_MODE === "test" ? testData : props.realData;

  return (
    <Dialog
      open={true}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 1,
            padding: "1vh",
            minHeight: "65vh",
          },
        },
      }}
    >
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
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
              Classification Model Selection
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Typography
            variant="subtitle1"
            sx={{ marginTop: 1, marginBottom: 2, fontSize: "1.5vh" }}
          >
            Model Selection:
          </Typography>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "repeat(2, 1fr)",
              gap: 1,
              maxHeight: "40vh",
              overflowY: "auto",
              borderBottom: 2,
              borderColor: "darkgrey",
            }}
          >
            {dataToDisplay.map((data, index) => (
              <Box
                key={index}
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  border: "1px solid lightgrey",
                  borderRadius: "4px",
                  padding: "1vh",
                  cursor: "pointer",
                  backgroundColor:
                    props.selectedModel === data.model_name
                      ? "#f0f0f0"
                      : "#fff",
                  "&:hover": {
                    backgroundColor: "#e0e0e0",
                  },
                  width: "34vh",
                  height: "24vh",
                  maxWidth: "350px",
                  maxHeight: "200px",
                }}
                onClick={() => {
                  selectModel(data.model_name);
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    width: "34vh",
                    height: "16vh",
                    maxWidth: "350px",
                    maxHeight: "200px",
                  }}
                >
                  <Typography fontSize={20} variant="h6">
                    {data.model_name}
                  </Typography>
                  <Radio
                    checked={props.selectedModel === data.model_name}
                    onChange={() => {
                      selectModel(data.model_name);
                    }}
                    value={data.model_name}
                  />
                </Box>
                <Typography
                  variant="body2"
                  sx={{ fontWeight: "bold", marginBottom: 1 }}
                >
                  {data.description}
                </Typography>
                <Typography variant="body2" sx={{ marginBottom: 1 }}>
                  Date: {data.creation_date}
                </Typography>
                <Typography variant="body2" sx={{ marginBottom: 1 }}>
                  Version: {data.version}
                </Typography>
                {/* Add more details as needed */}
              </Box>
            ))}
          </Box>
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              marginTop: "3vh",
            }}
          >
            <Button
              variant="outlined"
              onClick={() => {
                close();
              }}
              sx={{
                borderRadius: "0.4vh",
                paddingTop: "0.6vh",
                paddingBottom: "0.6vh",
                paddingLeft: "2vh",
                paddingRight: "2vh",
                fontSize: "1.17vh",
                border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                color: colours.CFIA_Background_Blue,
                "&:hover": {
                  backgroundColor: colours.CFIA_Background_Blue,
                  color: colours.CFIA_Background_White,
                  border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                  transition: "0.2s ease-in-out all",
                },
              }}
            >
              Done
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default SwitchModel;
