import {
  Autocomplete,
  Box,
  Button,
  Dialog,
  DialogContent,
  FilterOptionsState,
  FormControl,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListSubheader,
  Stack,
  TextField,
  Typography,
  createFilterOptions,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import { colours } from "@styles/colours";
import {
  ChangeEvent,
  Dispatch,
  SetStateAction,
  SyntheticEvent,
  useEffect,
  useMemo,
  useState,
} from "react";
import { batchUploadImage, batchUploadInit } from "@common/api";
import { validateImageFile } from "@common";
import { BatchUploadMetadata, SpeciesData } from "@common/types";
import { useSpeciesData } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import {
  folderNameSchema,
  seedCountSchema,
  zoomLevelSchema,
  fileListSchema,
  classLabelSchema,
} from "@common/validation";

interface params {
  setBatchUploadOpen: Dispatch<SetStateAction<boolean>>;
  backendUrl: string;
  containerName: string;
  uuid: string;
  apiScopeClaim: string;
}

const BatchUploadPopup = (props: params) => {
  const { setBatchUploadOpen, containerName, uuid, backendUrl, apiScopeClaim } =
    props;

  const [files, setFiles] = useState<FileList | null>(null);
  const [fileCount, setFileCount] = useState<number>(0);
  const [fileStatus, setFileStatus] = useState<boolean[]>([]);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadTotalProgress, setUploadTotalProgress] = useState<number>(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<boolean>(false);

  const [folderName, setFolderName] = useState<string>("");
  const [seedId, setSeedId] = useState<string>("");
  const [zoom, setZoom] = useState<number>(0);
  const [seedCount, setSeedCount] = useState<number>(0);
  const [sessionId, setSessionId] = useState<string>("");

  // Validation error states
  const [folderNameError, setFolderNameError] = useState<string>("");
  const [seedCountError, setSeedCountError] = useState<string>("");
  const [zoomError, setZoomError] = useState<string>("");
  const [filesError, setFilesError] = useState<string>("");
  const [classError, setClassError] = useState<string>("");

  const { speciesData } = useSpeciesData(backendUrl, apiScopeClaim);
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const classList = useMemo(() => {
    if (!speciesData?.seeds) return [];
    return speciesData.seeds.map((seed, index) => ({
      ...seed,
      id: index,
    }));
  }, [speciesData]);

  const defaultClass = useMemo(() => {
    return {
      id: -1,
      seed_id: "",
      name_code: "",
      family: "",
      genus: "",
      species: "",
      label: "",
    };
  }, []);
  const [selectedClass, setSelectedClass] = useState<SpeciesData | null>(null);
  const filter = createFilterOptions<SpeciesData>();

  const filteredClassList = (
    options: SpeciesData[],
    params: FilterOptionsState<SpeciesData>,
  ): SpeciesData[] => {
    const { inputValue } = params;
    if (inputValue === "") {
      return options;
    }
    const filtered = filter(options, params);

    // Suggest the creation of a new value
    const isExisting = options.some((option) => inputValue === option.label);
    if (inputValue !== "" && !isExisting) {
      filtered.push({
        ...defaultClass,
        label: `"${inputValue}"`,
      });
    }

    return filtered;
  };

  const getClassLabel = (option: string | SpeciesData): string => {
    return typeof option === "string" ? option : option.label || "";
  };

  const handleClassChange = (
    event: SyntheticEvent<Element, Event>,
    newValue: string | SpeciesData | null,
  ) => {
    event.preventDefault();
    if (newValue == null) {
      setSelectedClass(null);
    } else if (typeof newValue === "string") {
      setSelectedClass({
        ...defaultClass,
        label: newValue,
      });
    } else {
      setSelectedClass(newValue);
      setSeedId(newValue.seed_id);
    }
  };

  const handleFilesSelected = async (
    event: ChangeEvent<HTMLInputElement>,
  ): Promise<void> => {
    const selectedFiles = event.target.files;
    if (selectedFiles !== null) {
      // Basic validation first (count, etc.)
      const validationResult = fileListSchema.safeParse(selectedFiles);
      if (!validationResult.success) {
        setFilesError(validationResult.error.issues[0].message);
        return;
      }

      // Comprehensive validation for each file including dimensions
      const errors: string[] = [];
      for (let i = 0; i < selectedFiles.length; i++) {
        const fileValidation = await validateImageFile(selectedFiles[i]);
        if (!fileValidation.isValid) {
          errors.push(
            `${selectedFiles[i].name}: ${fileValidation.errors.join(", ")}`,
          );
        }
      }

      if (errors.length > 0) {
        setFilesError(`File validation failed:\n${errors.join("\n")}`);
        return;
      }

      // Clear any previous errors
      setFilesError("");
      setFiles(selectedFiles);
      setFileCount(selectedFiles.length);
      setFileStatus(new Array(selectedFiles.length).fill(false));
    }
  };

  const resetUpload = (): void => {
    setUploading(false);
    setUploadTotalProgress(0);
    setUploadError(null);
    setUploadSuccess(false);
  };

  const resetForm = (): void => {
    setFolderName("");
    setSelectedClass(null);
    setSeedCount(0);
    setZoom(0);
    setFiles(null);
    setFileCount(0);
    setFileStatus([]);
    setSessionId("");
  };

  const handleUpload = (): void => {
    if (!isAuthenticated) {
      setUploadError("You must be signed in to upload files");
      return;
    }

    // Clear previous errors
    setUploadError(null);
    setFolderNameError("");
    setSeedCountError("");
    setZoomError("");
    setFilesError("");
    setClassError("");

    // Validate folder name
    const folderValidation = folderNameSchema.safeParse(folderName);
    if (!folderValidation.success) {
      setFolderNameError(folderValidation.error.issues[0].message);
      return;
    }

    // Validate seed count
    const seedCountValidation = seedCountSchema.safeParse(seedCount);
    if (!seedCountValidation.success) {
      setSeedCountError(seedCountValidation.error.issues[0].message);
      return;
    }

    // Validate zoom level
    const zoomValidation = zoomLevelSchema.safeParse(zoom);
    if (!zoomValidation.success) {
      setZoomError(zoomValidation.error.issues[0].message);
      return;
    }

    // Validate files
    if (files == null) {
      setFilesError("Please select files to upload");
      return;
    }
    const filesValidation = fileListSchema.safeParse(files);
    if (!filesValidation.success) {
      setFilesError(filesValidation.error.issues[0].message);
      return;
    }

    // Validate class selection
    if (selectedClass == null) {
      setClassError("Please select a class");
      return;
    }

    // Validate class label if it's a custom class
    if (selectedClass.label && selectedClass.id === -1) {
      const classValidation = classLabelSchema.safeParse(selectedClass.label);
      if (!classValidation.success) {
        setClassError(classValidation.error.issues[0].message);
        return;
      }
    }

    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
      return;
    }

    resetUpload();
    setUploading(true);

    acquireAccessToken(msalInstance, [apiScopeClaim])
      .then((accessToken) => {
        return batchUploadInit({
          backendUrl,
          accessToken,
          folderName,
          containerUuid: containerName,
          fileCount,
        });
      })
      .then((response) => {
        setSessionId(response.session_id);
      })
      .catch((error) => {
        setUploadError(error.toString());
      });
  };

  const handleClose = (): void => {
    // setUploadError(null);
    resetUpload();
    resetForm();
    setBatchUploadOpen(false);
  };

  useEffect(() => {
    if (fileStatus.length === 0) {
      return;
    }
    if (fileStatus.some((status) => status === false)) {
      return;
    }
    setUploadSuccess(true);
  }, [fileStatus]);

  useEffect(() => {
    if (sessionId === "" || files == null) {
      return;
    }
    if (files == null || files.length === 0) {
      return;
    }
    if (!uploading) {
      return;
    }

    const uploadImage = (file: File): Promise<boolean> => {
      return new Promise((resolve, reject) => {
        if (file == null) {
          reject("No file selected");
        }
        const reader = new FileReader();
        reader.onloadend = () => {
          const imageDataUrl = reader.result;
          if (typeof imageDataUrl !== "string") {
            reject("Invalid file type");
            return;
          }
          const data: BatchUploadMetadata = {
            containerName: containerName,
            uuid: uuid,
            seedId: seedId,
            seedName: selectedClass?.label ?? "", // TODO: remove when backend is implemented
            zoom: zoom,
            seedCount: seedCount,
            imageDataUrl: imageDataUrl,
            sessionId: sessionId,
          };

          acquireAccessToken(msalInstance, [apiScopeClaim])
            .then((accessToken) => {
              return batchUploadImage({
                backendUrl: backendUrl,
                data: data,
                accessToken: accessToken,
              });
            })
            .then((response) => {
              if (response) {
                console.log("Successfully uploaded image: ", file.name);
              }
              resolve(true);
            })
            .catch((error) => {
              console.error("Error uploading image: ", file.name);
              reject(error);
            });
        };
        reader.readAsDataURL(file);
      });
    };

    const batchUpload = async () => {
      const uploadPromises: Promise<boolean>[] = [];
      fileStatus.map((status, index) => {
        if (!status) {
          const promise = uploadImage(files[index])
            .then((response) => {
              if (response) {
                setFileStatus((prev) => {
                  const newStatus = [...prev];
                  newStatus[index] = response;
                  return newStatus;
                });
                setUploadTotalProgress((prev) => prev + 1);
              }
              return Promise.resolve(true);
            })
            .catch((error) => {
              console.error(error);
              return Promise.resolve(false);
            });

          uploadPromises.push(promise);
        }
        return Promise.resolve(true);
      });

      await Promise.all(uploadPromises);

      resetUpload();
    };

    batchUpload();
  }, [
    apiScopeClaim,
    backendUrl,
    containerName,
    fileStatus,
    files,
    msalInstance,
    seedCount,
    seedId,
    selectedClass?.label,
    sessionId,
    uploading,
    uuid,
    zoom,
  ]);

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
              Batch Upload Images
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <FormControl
            sx={{
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              width: "100%",
            }}
          >
            {uploadError && <p style={{ color: "red" }}>{uploadError}</p>}
            {uploading && (
              <Stack spacing={1} sx={{ width: "100%", marginBottom: "20px" }}>
                <LinearProgress
                  variant="determinate"
                  value={(uploadTotalProgress / fileCount) * 100}
                  sx={{ width: "100%", height: "10px" }}
                />
                <LinearProgress
                  variant="indeterminate"
                  sx={{ width: "100%", height: "10px" }}
                />
              </Stack>
            )}

            <TextField
              id="input-folder-name"
              label="Folder Name"
              variant="outlined"
              value={folderName}
              onChange={(e) => {
                setFolderName(e.target.value);
                if (folderNameError) setFolderNameError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              inputProps={{
                min: 1,
                max: 100,
                style: { textAlign: "center" },
              }}
              error={!!folderNameError}
              helperText={folderNameError}
              disabled={uploading}
            />

            <Autocomplete
              id="input-seed-class"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Class"
                  error={!!classError}
                  helperText={classError}
                />
              )}
              options={classList}
              value={selectedClass}
              onChange={(event, newValue) => {
                handleClassChange(event, newValue);
                if (classError) setClassError("");
              }}
              isOptionEqualToValue={(option, value) =>
                option.label === value.label
              }
              filterOptions={filteredClassList}
              disablePortal
              selectOnFocus
              clearOnBlur
              handleHomeEndKeys
              freeSolo={false}
              getOptionLabel={getClassLabel}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              disabled={uploading}
            />

            <TextField
              id="input-seed-count"
              label="Seed Count"
              variant="outlined"
              type="number"
              value={seedCount > 0 ? seedCount : ""}
              onChange={(e) => {
                setSeedCount(parseInt(e.target.value) || 0);
                if (seedCountError) setSeedCountError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              inputProps={{
                min: 1,
                max: 100,
                style: { textAlign: "center" },
              }}
              error={!!seedCountError}
              helperText={seedCountError}
              disabled={uploading}
            />
            <TextField
              id="input-zoom-level"
              label="Zoom Level"
              variant="outlined"
              type="number"
              value={zoom > 0 ? zoom : ""}
              onChange={(e) => {
                setZoom(parseInt(e.target.value) || 0);
                if (zoomError) setZoomError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              inputProps={{
                min: 1,
                max: 100,
                style: { textAlign: "center" },
              }}
              error={!!zoomError}
              helperText={zoomError}
              disabled={uploading}
            />

            <Button
              variant="contained"
              component="label"
              sx={{
                marginTop: "10px",
                width: "fit-content",
              }}
              disabled={uploading}
            >
              Select Files
              <input
                type="file"
                multiple
                accept="image/png"
                onChange={handleFilesSelected}
                hidden
              />
            </Button>
            {filesError && (
              <Typography
                variant="caption"
                color="error"
                sx={{ marginTop: "5px", fontSize: "0.75rem" }}
              >
                {filesError}
              </Typography>
            )}
            {/* scrollable list of file names */}
            {files && fileCount > 0 && (
              <Box
                sx={{
                  width: "100%",
                  height: "fit-content",
                  maxHeight: "200px",
                  overflow: "auto",
                  marginTop: "10px",
                  border: "1px solid lightgrey",
                  borderRadius: "5px",
                  padding: "5px",
                }}
              >
                <List
                  dense={true}
                  subheader={
                    <ListSubheader component="div" id="nested-list-subheader">
                      Transfer Status
                    </ListSubheader>
                  }
                >
                  {fileStatus.map((value, index) => {
                    return (
                      <ListItem key={index}>
                        {value ? (
                          <CheckCircleOutlinedIcon
                            sx={{
                              color: "green",
                              marginRight: "10px",
                            }}
                          />
                        ) : (
                          <CancelOutlinedIcon
                            sx={{
                              color: "red",
                              marginRight: "10px",
                            }}
                          />
                        )}
                        <ListItemText
                          primary={files[index].name}
                          secondary={null}
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
                marginTop: "20px",
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
                  onClick={handleUpload}
                >
                  Upload
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
                onClick={handleClose}
              >
                {uploadSuccess ? "Close" : "Cancel"}
              </Button>
            </Box>
          </FormControl>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default BatchUploadPopup;
