import {
  Box,
  Button,
  Dialog,
  DialogContent,
  FormControl,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListSubheader,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import { colours } from "@styles/colours";
import { ChangeEvent } from "react";
import { useTranslation } from "react-i18next";
import { DeviceSelectionFields } from "@components/common/DeviceSelectionFields";
import { TaxonomicFieldsGroup } from "../taxonomic_fields_group/TaxonomicFieldsGroup";
import { FolderFieldsGroup } from "../folder_fields_group/FolderFieldsGroup";
import { SpeciesData, ApiDevicesResponse } from "@common/types";
import {
  BatchSessionInfo,
  UploadWorkflowInfo,
} from "@stores/useBatchUploadStore";

export interface BatchUploadPopupViewProps {
  // Dialog control
  onClose: () => void;

  // Upload state
  uploading: boolean;
  uploadError: string | null;
  uploadSuccess: boolean;
  uploadProgress: number;

  // Form field values
  files: FileList | null;
  fileCount: number;
  folderName: string;
  folderDescription: string;
  family: string;
  genus: string;
  species: string;
  nameCode: string;
  trayCode: string;
  sampleId: string;
  deviceBrandId: string;
  deviceModelId: string;
  deviceLensId: string;
  magnification: number;

  // Form field change handlers
  onFilesSelected: (event: ChangeEvent<HTMLInputElement>) => Promise<void>;
  onFolderNameChange: (value: string) => void;
  onFolderDescriptionChange: (value: string) => void;
  onFamilyChange: (value: string) => void;
  onGenusChange: (value: string) => void;
  onSpeciesChange: (value: string) => void;
  onNameCodeChange: (value: string) => void;
  onTrayCodeChange: (value: string) => void;
  onSampleIdChange: (value: string) => void;
  onDeviceBrandChange: (value: string) => void;
  onDeviceModelChange: (value: string) => void;
  onDeviceLensChange: (value: string) => void;
  onMagnificationChange: (value: number) => void;

  // Validation errors
  folderNameError: string;
  folderDescriptionError: string;
  familyError: string;
  genusError: string;
  speciesError: string;
  nameCodeError: string;
  trayCodeError: string;
  sampleIdError: string;
  deviceBrandError: string;
  deviceModelError: string;
  deviceLensError: string;
  magnificationError: string;
  filesError: string;

  // Action handlers
  onCreateFolder: () => void;
  onUpload: () => void;

  // Folder creation state
  createdFolderId: string;
  creatingFolder: boolean;

  // Data from API
  speciesData: SpeciesData[];
  devicesData: ApiDevicesResponse | null;

  // Upload session state
  currentSession: BatchSessionInfo | null;
  uploads: Map<string, UploadWorkflowInfo>;
}

export const BatchUploadPopupView = (props: BatchUploadPopupViewProps) => {
  const { t } = useTranslation("popups");

  const {
    onClose,
    uploading,
    uploadError,
    uploadSuccess,
    uploadProgress,
    files,
    fileCount,
    folderName,
    folderDescription,
    family,
    genus,
    species,
    nameCode,
    trayCode,
    sampleId,
    deviceBrandId,
    deviceModelId,
    deviceLensId,
    magnification,
    onFilesSelected,
    onFolderNameChange,
    onFolderDescriptionChange,
    onFamilyChange,
    onGenusChange,
    onSpeciesChange,
    onNameCodeChange,
    onTrayCodeChange,
    onSampleIdChange,
    onDeviceBrandChange,
    onDeviceModelChange,
    onDeviceLensChange,
    onMagnificationChange,
    folderNameError,
    folderDescriptionError,
    familyError,
    genusError,
    speciesError,
    nameCodeError,
    trayCodeError,
    sampleIdError,
    deviceBrandError,
    deviceModelError,
    deviceLensError,
    magnificationError,
    filesError,
    onCreateFolder,
    onUpload,
    createdFolderId,
    creatingFolder,
    speciesData,
    devicesData,
    currentSession,
    uploads,
  } = props;

  return (
    <Dialog
      open={true}
      onClose={onClose}
      maxWidth="lg"
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
      <DialogContent sx={{ height: "80vh", padding: "16px" }}>
        {/* Header */}
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
              fontSize: "2vh",
              color: colours.CFIA_Font_Black,
            }}
          >
            {t("batchUpload.title")}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* 2-Column Layout */}
        <Box sx={{ display: "flex", gap: 2, height: "calc(100% - 60px)" }}>
          {/* LEFT COLUMN - Form Fields */}
          <Box sx={{ flex: 1 }}>
            <Box
              sx={{
                height: "100%",
                overflowY: "auto",
                paddingRight: "8px",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <FormControl
                sx={{
                  display: "flex",
                  flexDirection: "column",
                  width: "100%",
                  gap: "10px",
                }}
              >
                {uploadError && <p style={{ color: "red" }}>{uploadError}</p>}
                {uploading && currentSession && (
                  <Stack spacing={1} sx={{ width: "100%" }}>
                    <LinearProgress
                      variant="determinate"
                      value={uploadProgress}
                      sx={{ width: "100%", height: "10px" }}
                    />
                    <Typography variant="caption" sx={{ textAlign: "center" }}>
                      {currentSession.completedFiles} of{" "}
                      {currentSession.totalFiles} completed
                      {currentSession.failedFiles > 0 &&
                        ` (${currentSession.failedFiles} failed)`}
                    </Typography>
                    <LinearProgress
                      variant="indeterminate"
                      sx={{ width: "100%", height: "10px" }}
                    />
                  </Stack>
                )}

                <TaxonomicFieldsGroup
                  speciesData={speciesData}
                  family={family}
                  genus={genus}
                  species={species}
                  nameCode={nameCode}
                  onFamilyChange={onFamilyChange}
                  onGenusChange={onGenusChange}
                  onSpeciesChange={onSpeciesChange}
                  onNameCodeChange={onNameCodeChange}
                  familyError={familyError}
                  genusError={genusError}
                  speciesError={speciesError}
                  nameCodeError={nameCodeError}
                  disabled={uploading}
                  sx={{ width: "100%" }}
                />

                <TextField
                  id="input-tray-code"
                  label={t("batchUpload.metadataSection.trayCodeLabel")}
                  variant="outlined"
                  select
                  value={trayCode}
                  onChange={(e) => onTrayCodeChange(e.target.value)}
                  sx={{
                    width: "100%",
                  }}
                  error={!!trayCodeError}
                  helperText={trayCodeError}
                  disabled={uploading}
                >
                  <MenuItem value="">
                    <em>{t("batchUpload.metadataSection.selectTrayCode")}</em>
                  </MenuItem>
                  <MenuItem value="A">A</MenuItem>
                  <MenuItem value="B">B</MenuItem>
                  <MenuItem value="C">C</MenuItem>
                  <MenuItem value="D">D</MenuItem>
                  <MenuItem value="E">E</MenuItem>
                </TextField>

                <TextField
                  id="input-magnification"
                  label={t("batchUpload.deviceSection.magnificationLabel")}
                  variant="outlined"
                  type="number"
                  value={magnification > 0 ? magnification : ""}
                  onChange={(e) =>
                    onMagnificationChange(parseFloat(e.target.value) || 0)
                  }
                  sx={{
                    width: "100%",
                  }}
                  slotProps={{
                    htmlInput: {
                      min: 0.1,
                      max: 1000,
                      step: 0.1,
                      style: { textAlign: "center" },
                    },
                  }}
                  error={!!magnificationError}
                  helperText={magnificationError}
                  disabled={uploading}
                />

                <TextField
                  id="input-sample-id"
                  label={t("batchUpload.metadataSection.sampleIdLabel")}
                  variant="outlined"
                  value={sampleId}
                  onChange={(e) => onSampleIdChange(e.target.value)}
                  sx={{
                    width: "100%",
                  }}
                  error={!!sampleIdError}
                  helperText={sampleIdError}
                  disabled={uploading}
                />

                <DeviceSelectionFields
                  selectedBrandId={deviceBrandId}
                  selectedModelId={deviceModelId}
                  selectedLensId={deviceLensId}
                  onBrandChange={onDeviceBrandChange}
                  onModelChange={onDeviceModelChange}
                  onLensChange={onDeviceLensChange}
                  devicesData={devicesData}
                  disabled={uploading}
                  brandError={deviceBrandError}
                  modelError={deviceModelError}
                  lensError={deviceLensError}
                />

                <FolderFieldsGroup
                  folderName={folderName}
                  folderDescription={folderDescription}
                  onFolderNameChange={onFolderNameChange}
                  onFolderDescriptionChange={onFolderDescriptionChange}
                  folderNameError={folderNameError}
                  folderDescriptionError={folderDescriptionError}
                  disabled={uploading || creatingFolder}
                  sx={{ width: "100%", marginTop: "10px" }}
                />

                {/* Create Folder Button */}
                <Button
                  variant="contained"
                  onClick={onCreateFolder}
                  disabled={
                    uploading ||
                    creatingFolder ||
                    !folderName ||
                    !!createdFolderId
                  }
                  sx={{
                    width: "100%",
                    backgroundColor: createdFolderId ? "#4caf50" : undefined,
                  }}
                >
                  {creatingFolder
                    ? t("batchUpload.folderActions.creatingButton")
                    : createdFolderId
                      ? t("batchUpload.folderActions.createdButton")
                      : t("batchUpload.folderActions.createButton")}
                </Button>
              </FormControl>
            </Box>
          </Box>

          {/* RIGHT COLUMN - File Selection and List */}
          <Box sx={{ flex: 1, width: "97%" }}>
            <Box
              sx={{
                height: "100%",
                overflowY: "auto",
                paddingLeft: "8px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
              }}
            >
              <Button
                variant="contained"
                component="label"
                sx={{
                  width: "fit-content",
                  alignSelf: "center",
                }}
                disabled={uploading || !createdFolderId}
              >
                {t("batchUpload.filesSection.selectFiles")}
                <input
                  type="file"
                  multiple
                  accept="image/png"
                  onChange={onFilesSelected}
                  hidden
                />
              </Button>

              {filesError && (
                <Typography
                  variant="caption"
                  color="error"
                  sx={{ fontSize: "0.75rem", alignSelf: "center" }}
                >
                  {filesError}
                </Typography>
              )}

              {/* scrollable list of file names with upload status */}
              {files && fileCount > 0 && (
                <Box
                  sx={{
                    width: "100%",
                    flex: 1,
                    overflow: "auto",
                    border: "1px solid lightgrey",
                    borderRadius: "5px",
                    padding: "5px",
                  }}
                >
                  <List
                    dense={true}
                    subheader={
                      <ListSubheader component="div" id="nested-list-subheader">
                        {t("batchUpload.filesSection.uploadStatus")}
                      </ListSubheader>
                    }
                  >
                    {Array.from({ length: fileCount }).map((_, index) => {
                      const file = files[index];
                      // Find upload info from Zustand store by matching file name
                      const uploadInfo = Array.from(uploads.values()).find(
                        (u) => u.fileName === file.name,
                      );
                      const status = uploadInfo?.status || "pending";

                      return (
                        <ListItem key={index}>
                          {status === "completed" ? (
                            <CheckCircleOutlinedIcon
                              sx={{
                                color: "green",
                                marginRight: "10px",
                              }}
                            />
                          ) : status === "failed" ? (
                            <CancelOutlinedIcon
                              sx={{
                                color: "red",
                                marginRight: "10px",
                              }}
                            />
                          ) : (
                            <CancelOutlinedIcon
                              sx={{
                                color: "grey",
                                marginRight: "10px",
                              }}
                            />
                          )}
                          <ListItemText
                            primary={file.name}
                            secondary={
                              uploadInfo?.error
                                ? t("batchUpload.queue.errorMessage", {
                                    message: uploadInfo.error,
                                  })
                                : status === "queued"
                                  ? t("batchUpload.queue.queued", {
                                      position: uploadInfo?.queuePosition ?? "",
                                    })
                                  : status === "processing"
                                    ? t("batchUpload.queue.processing")
                                    : status === "completed"
                                      ? t("batchUpload.queue.completed")
                                      : status === "failed"
                                        ? t("batchUpload.queue.failed")
                                        : t("batchUpload.queue.pending")
                            }
                            sx={{
                              whiteSpace: "nowrap",
                              userSelect: "none",
                            }}
                          />
                        </ListItem>
                      );
                    })}
                  </List>
                </Box>
              )}

              <Box
                sx={{
                  display: "flex",
                  flexDirection: "row",
                  justifyContent: "space-evenly",
                  alignItems: "center",
                  marginTop: "auto",
                  paddingTop: "20px",
                }}
              >
                {!uploading && !uploadSuccess && (
                  <Button
                    sx={{
                      backgroundColor: "green",
                      color: "white",
                      "&:hover": {
                        backgroundColor: "green",
                        opacity: 0.6,
                      },
                      marginRight: "10px",
                    }}
                    onClick={onUpload}
                  >
                    {t("batchUpload.uploadSection.uploadButton")}
                  </Button>
                )}
                <Button
                  sx={{
                    backgroundColor: "red",
                    color: "white",
                    "&:hover": {
                      backgroundColor: "red",
                      opacity: 0.5,
                    },
                  }}
                  onClick={onClose}
                >
                  {uploadSuccess
                    ? t("batchUpload.uploadSection.closeButton")
                    : t("batchUpload.uploadSection.cancelButton")}
                </Button>
              </Box>
            </Box>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};
