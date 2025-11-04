import React, { useState } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Radio,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import testData from "../../../static_data/static_model_data.json";
import { PopupActionButtons } from "@components/common";
import { useModalStore } from "@stores/useModalStore";
import { useModelStore } from "@stores/useModelStore";
import { useTranslation } from "react-i18next";

const SwitchModel: React.FC = () => {
  const { t } = useTranslation("popups");
  const { closeModelInfoPopup } = useModalStore();
  const { selectedModel, metadata, setSelectedModel } = useModelStore();
  const [tempSelectedModel, setTempSelectedModel] = useState<string>(
    selectedModel ?? "",
  );

  const handleClose = (): void => {
    closeModelInfoPopup();
  };

  const selectModel = (model: string): void => {
    console.log("Model selected:", model);
    setTempSelectedModel(model);
  };

  const handleSave = (): void => {
    setSelectedModel(tempSelectedModel);
    handleClose();
  };

  const handleCancel = (): void => {
    handleClose();
  };

  const dataToDisplay =
    process.env.VITE_APP_MODE === "test" ? testData : metadata;

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
              {t("modelSelection.title")}
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Typography
            variant="subtitle1"
            sx={{ marginTop: 1, marginBottom: 2, fontSize: "1.5vh" }}
          >
            {t("modelSelection.subtitle")}
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
                    tempSelectedModel === data.pipelineId ? "#f0f0f0" : "#fff",
                  "&:hover": {
                    backgroundColor: "#e0e0e0",
                  },
                  width: "34vh",
                  height: "24vh",
                  maxWidth: "350px",
                  maxHeight: "200px",
                }}
                onClick={() => {
                  selectModel(data.pipelineId);
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
                    {data.modelName}
                  </Typography>
                  <Radio
                    checked={tempSelectedModel === data.pipelineId}
                    onChange={() => {
                      selectModel(data.pipelineId);
                    }}
                    value={data.pipelineId}
                  />
                </Box>
                <Typography
                  variant="body2"
                  sx={{ fontWeight: "bold", marginBottom: 1 }}
                >
                  {data.description}
                </Typography>
                <Typography variant="body2" sx={{ marginBottom: 1 }}>
                  {t("modelSelection.date", { date: data.creationDate })}
                </Typography>
                <Typography variant="body2" sx={{ marginBottom: 1 }}>
                  {t("modelSelection.version", { version: data.version })}
                </Typography>
                {/* Add more details as needed */}
              </Box>
            ))}
          </Box>
        </Box>
      </DialogContent>
      <PopupActionButtons
        onSave={handleSave}
        onCancel={handleCancel}
        sx={{ padding: "1vh 2vh" }}
      />
    </Dialog>
  );
};

export default SwitchModel;
