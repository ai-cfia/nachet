import React from "react";
import { Overlay, InfoContainer } from "./indexElements";
import { Box, CardHeader, IconButton, Button } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import Radio from "@mui/material/Radio";
import Typography from "@mui/material/Typography";
import testData from "../../../static_data/static_model_data.json";

interface params {
  setSwitchModelOpen: React.Dispatch<React.SetStateAction<boolean>>;
  switchModelOpen: boolean;
  selectedModel: string;
  setSelectedModel: React.Dispatch<React.SetStateAction<string>>;
  realData: any[]; // Type should be adjusted to match the actual data structure
}

const SwitchModel: React.FC<params> = (props): JSX.Element => {
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
    <Overlay>
      <Box
        sx={{
          position: "relative",
          width: "50vw",
          height: "65vh",
          zIndex: 30,
          border: `0.01vh solid LightGrey`,
          borderRadius: 1,
          background: colours.CFIA_Background_White,
        }}
        boxShadow={1}
      >
        <CardHeader
          title="Classification Model Selection"
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
          <Typography
            variant="subtitle1"
            sx={{ marginTop: 1, marginBottom: 2 }}
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
        </InfoContainer>
        <Button
          color="inherit"
          variant="outlined"
          onClick={() => {
            close();
          }}
          style={{
            marginTop: "30px",
            display: "block",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
            <span>Done</span>
          </div>
        </Button>
      </Box>
    </Overlay>
  );
};

export default SwitchModel;
