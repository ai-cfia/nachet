import styled from "styled-components";
import {
  Autocomplete,
  Box,
  Button,
  CardHeader,
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
  createFilterOptions,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import CheckCircleOutlinedIcon from "@mui/icons-material/CheckCircleOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import { colours } from "../../../styles/colours";
import {
  ChangeEvent,
  Dispatch,
  SetStateAction,
  SyntheticEvent,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  batchUploadImage,
  batchUploadInit,
  requestClassList,
} from "../../../common/api";
import { BatchUploadMetadata, ClassData } from "../../../common/types";

export const Overlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 20;
  display: flex;
  justify-content: center;
  align-items: center;
  transition:
    visibility 0.5s,
    opacity 0.5s;
`;

export const InfoContainer = styled.div`
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-width: 100%;
  width: 100%;
`;

interface params {
  setBatchUploadOpen: Dispatch<SetStateAction<boolean>>;
  backendUrl: string;
  containerName: string;
  uuid: string;
}

const BatchUploadPopup = (props: params): JSX.Element => {
  const { setBatchUploadOpen, containerName, uuid, backendUrl } = props;

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

  const [classList, setClassList] = useState<ClassData[]>([]);

  const defaultClass = useMemo(() => {
    return {
      id: -1,
      classId: "",
      label: "",
    };
  }, []);
  const [selectedClass, setSelectedClass] = useState<ClassData | null>(null);
  const filter = createFilterOptions<ClassData>();

  const filteredClassList = (
    options: ClassData[],
    params: FilterOptionsState<ClassData>,
  ): ClassData[] => {
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

  const getClassLabel = (option: string | ClassData): string => {
    return typeof option === "string" ? option : option.label;
  };

  const handleClassChange = (
    event: SyntheticEvent<Element, Event>,
    newValue: string | ClassData | null,
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
      setSeedId(newValue.classId);
    }
  };

  const handleFilesSelected = (event: ChangeEvent<HTMLInputElement>): void => {
    // TODO validation
    const files = event.target.files;
    if (files !== null) {
      console.log(files);
      setFiles(files);
      setFileCount(files.length);
      setFileStatus(new Array(files.length).fill(false));
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
    resetUpload();
    if (selectedClass == null) {
      setUploadError("Please select a class");
      return;
    }
    if (seedCount < 1) {
      setUploadError("Please enter a seed count");
      return;
    }
    if (zoom < 1) {
      setUploadError("Please enter a zoom level");
      return;
    }
    if (files == null || files.length === 0) {
      setUploadError("Please select an image");
      return;
    }

    setUploading(true);

    batchUploadInit(backendUrl, uuid, folderName, containerName, fileCount)
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
    if (backendUrl == null || backendUrl === "") {
      return;
    }
    requestClassList(backendUrl)
      .then((response) => {
        const list: ClassData[] = [];
        response.seeds.forEach((element, index) => {
          list.push({
            id: index,
            classId: element.seed_id,
            label: element.seed_name,
          });
        });
        setClassList(list);
      })
      .catch((error) => {
        console.error("Error fetching class list: ", error);
      });
  }, [backendUrl]);

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
          batchUploadImage(backendUrl, data)
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
    sessionId,
    files,
    fileStatus,
    uploading,
    backendUrl,
    folderName,
    seedId,
    seedCount,
    selectedClass,
    zoom,
    containerName,
    uuid,
  ]);

  return (
    <Overlay>
      <Box
        sx={{
          width: "20%",
          height: "fit-content",
          zIndex: 30,
          border: `0.01vh solid LightGrey`,
          borderRadius: 1,
          background: colours.CFIA_Background_White,
          display: "flex",
          flexDirection: "column",
          padding: "10px",
        }}
        boxShadow={1}
      >
        <CardHeader
          title="Batch Upload Images"
          action={
            <IconButton onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          }
          sx={{
            display: "flex",
            width: "auto",
          }}
        />
        <InfoContainer>
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
              onChange={(e) => setFolderName(e.target.value)}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              inputProps={{
                min: 1,
                max: 100,
                style: { textAlign: "center" },
              }}
              disabled={uploading}
            />

            <Autocomplete
              id="input-seed-class"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Class"
                  error={selectedClass == null}
                />
              )}
              options={classList}
              value={selectedClass}
              onChange={handleClassChange}
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
              onChange={(e) => setSeedCount(parseInt(e.target.value))}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              inputProps={{
                min: 1,
                max: 100,
                style: { textAlign: "center" },
              }}
              error={seedCount < 1}
              disabled={uploading}
            />
            <TextField
              id="input-zoom-level"
              label="Zoom Level"
              variant="outlined"
              type="number"
              value={zoom > 0 ? zoom : ""}
              onChange={(e) => setZoom(parseInt(e.target.value))}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              inputProps={{
                min: 1,
                max: 100,
                style: { textAlign: "center" },
              }}
              error={zoom < 1}
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
                onChange={handleFilesSelected}
                hidden
              />
            </Button>
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
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default BatchUploadPopup;
