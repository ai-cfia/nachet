import {
  Autocomplete,
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
import {
  ChangeEvent,
  Dispatch,
  SetStateAction,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { batchUploadImage, batchUploadInit } from "@common/api";
import { validateImageFile } from "@common";
import { BatchUploadMetadata } from "@common/types";
import { useSpeciesData, useDeviceData } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import {
  folderNameSchema,
  magnificationSchema,
  trayCodeSchema,
  taxonomicFieldSchema,
  sampleIdSchema,
  deviceIdValidationSchema,
  fileListSchema,
} from "@common/validation";
import { useDeviceStore } from "@stores/useDeviceStore";
import { DeviceSelectionFields } from "@components/common/DeviceSelectionFields";

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
  const uploadSuccess = useMemo(() => {
    return fileStatus.length > 0 && fileStatus.every((status) => status);
  }, [fileStatus]);

  const [folderName, setFolderName] = useState<string>("");
  const [family, setFamily] = useState<string>("");
  const [genus, setGenus] = useState<string>("");
  const [species, setSpecies] = useState<string>("");
  const [nameCode, setNameCode] = useState<string>("");
  const [trayCode, setTrayCode] = useState<string>("");
  const [sampleId, setSampleId] = useState<string>("");
  const [deviceBrandId, setDeviceBrandId] = useState<string>("");
  const [deviceModelId, setDeviceModelId] = useState<string>("");
  const [deviceLensId, setDeviceLensId] = useState<string>("");
  const [magnification, setMagnification] = useState<number>(0);
  const [sessionId, setSessionId] = useState<string>("");

  // Track if user has manually edited folder name
  const folderNameManuallyEdited = useRef<boolean>(false);

  // Validation error states
  const [folderNameError, setFolderNameError] = useState<string>("");
  const [familyError, setFamilyError] = useState<string>("");
  const [genusError, setGenusError] = useState<string>("");
  const [speciesError, setSpeciesError] = useState<string>("");
  const [nameCodeError, setNameCodeError] = useState<string>("");
  const [trayCodeError, setTrayCodeError] = useState<string>("");
  const [sampleIdError, setSampleIdError] = useState<string>("");
  const [deviceBrandError, setDeviceBrandError] = useState<string>("");
  const [deviceModelError, setDeviceModelError] = useState<string>("");
  const [deviceLensError, setDeviceLensError] = useState<string>("");
  const [magnificationError, setMagnificationError] = useState<string>("");
  const [filesError, setFilesError] = useState<string>("");

  const { speciesData } = useSpeciesData(backendUrl, apiScopeClaim);
  const { devicesData } = useDeviceData(backendUrl, apiScopeClaim);
  const { deviceSelection } = useDeviceStore();
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  // Get unique values for each taxonomic field
  const availableFamilies = useMemo(() => {
    if (!speciesData?.seeds) return [];
    return Array.from(
      new Set(speciesData.seeds.map((seed) => seed.family)),
    ).sort();
  }, [speciesData]);

  const availableGenera = useMemo(() => {
    if (!speciesData?.seeds) return [];
    const filtered = speciesData.seeds.filter(
      (seed) => !family || seed.family === family,
    );
    return Array.from(new Set(filtered.map((seed) => seed.genus))).sort();
  }, [speciesData, family]);

  const availableSpecies = useMemo(() => {
    if (!speciesData?.seeds) return [];
    const filtered = speciesData.seeds.filter(
      (seed) =>
        (!family || seed.family === family) && (!genus || seed.genus === genus),
    );
    return Array.from(new Set(filtered.map((seed) => seed.species))).sort();
  }, [speciesData, family, genus]);

  const availableNameCodes = useMemo(() => {
    if (!speciesData?.seeds) return [];
    const filtered = speciesData.seeds.filter(
      (seed) =>
        (!family || seed.family === family) &&
        (!genus || seed.genus === genus) &&
        (!species || seed.species === species),
    );
    return Array.from(new Set(filtered.map((seed) => seed.name_code))).sort();
  }, [speciesData, family, genus, species]);

  // Normalize folder name (genus-species pattern)
  const normalizeFolderName = (
    genusVal: string,
    speciesVal: string,
  ): string => {
    const normalizeText = (text: string) =>
      text.toLowerCase().replace(/[^a-z]/g, "");
    const normalizedGenus = normalizeText(genusVal);
    const normalizedSpecies = normalizeText(speciesVal);
    return normalizedGenus && normalizedSpecies
      ? `${normalizedGenus}-${normalizedSpecies}`
      : "";
  };

  // Suggested folder name based on genus and species
  const suggestedFolderName = useMemo(() => {
    if (genus && species) {
      return normalizeFolderName(genus, species);
    }
    return "";
  }, [genus, species]);

  // Auto-populate other fields when name_code is selected (most specific)
  const handleNameCodeChange = (value: string) => {
    setNameCode(value);
    if (value && speciesData?.seeds) {
      const matchingSeed = speciesData.seeds.find(
        (seed) => seed.name_code === value,
      );
      if (matchingSeed) {
        setFamily(matchingSeed.family);
        setGenus(matchingSeed.genus);
        setSpecies(matchingSeed.species);
      }
    }
  };

  // Auto-populate family/genus when species is selected if only one option
  const handleSpeciesChange = (value: string) => {
    setSpecies(value);
    if (value && speciesData?.seeds) {
      const matchingSeeds = speciesData.seeds.filter(
        (seed) => seed.species === value,
      );
      const uniqueFamilies = Array.from(
        new Set(matchingSeeds.map((s) => s.family)),
      );
      const uniqueGenera = Array.from(
        new Set(matchingSeeds.map((s) => s.genus)),
      );

      if (uniqueFamilies.length === 1) setFamily(uniqueFamilies[0]);
      if (uniqueGenera.length === 1) setGenus(uniqueGenera[0]);
    }
  };

  // Initialize device selections from Zustand store (read-only, don't persist back)
  // We intentionally set state directly in this effect as we're synchronizing with external Zustand store
  useEffect(() => {
    if (deviceSelection) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDeviceBrandId(deviceSelection.selectedBrandId);
      setDeviceModelId(deviceSelection.selectedModelId);
      setDeviceLensId(deviceSelection.selectedLensId);
    }
  }, [deviceSelection]);

  // Auto-prefill folder name when both genus and species are set (only if not manually edited)
  useEffect(() => {
    if (suggestedFolderName && !folderNameManuallyEdited.current) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFolderName(suggestedFolderName);
    }
  }, [suggestedFolderName]);

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
  };

  const resetForm = (): void => {
    setFolderName("");
    setFamily("");
    setGenus("");
    setSpecies("");
    setNameCode("");
    setTrayCode("");
    setSampleId("");
    // Reset device fields to persisted values from store
    setDeviceBrandId(deviceSelection.selectedBrandId);
    setDeviceModelId(deviceSelection.selectedModelId);
    setDeviceLensId(deviceSelection.selectedLensId);
    setMagnification(0);
    setFiles(null);
    setFileCount(0);
    setFileStatus([]);
    setSessionId("");
    folderNameManuallyEdited.current = false;
  };

  const handleUpload = (): void => {
    if (!isAuthenticated) {
      setUploadError("You must be signed in to upload files");
      return;
    }

    // Clear previous errors
    setUploadError(null);
    setFolderNameError("");
    setFamilyError("");
    setGenusError("");
    setSpeciesError("");
    setNameCodeError("");
    setTrayCodeError("");
    setSampleIdError("");
    setDeviceBrandError("");
    setDeviceModelError("");
    setDeviceLensError("");
    setMagnificationError("");
    setFilesError("");

    // Validate folder name
    const folderValidation = folderNameSchema.safeParse(folderName);
    if (!folderValidation.success) {
      setFolderNameError(folderValidation.error.issues[0].message);
      return;
    }

    // Validate family
    const familyValidation = taxonomicFieldSchema.safeParse(family);
    if (!familyValidation.success) {
      setFamilyError(familyValidation.error.issues[0].message);
      return;
    }

    // Validate genus
    const genusValidation = taxonomicFieldSchema.safeParse(genus);
    if (!genusValidation.success) {
      setGenusError(genusValidation.error.issues[0].message);
      return;
    }

    // Validate species
    const speciesValidation = taxonomicFieldSchema.safeParse(species);
    if (!speciesValidation.success) {
      setSpeciesError(speciesValidation.error.issues[0].message);
      return;
    }

    // Validate name code
    const nameCodeValidation = taxonomicFieldSchema.safeParse(nameCode);
    if (!nameCodeValidation.success) {
      setNameCodeError(nameCodeValidation.error.issues[0].message);
      return;
    }

    // Validate tray code
    const trayCodeValidation = trayCodeSchema.safeParse(trayCode);
    if (!trayCodeValidation.success) {
      setTrayCodeError(trayCodeValidation.error.issues[0].message);
      return;
    }

    // Validate sample ID
    const sampleIdValidation = sampleIdSchema.safeParse(sampleId);
    if (!sampleIdValidation.success) {
      setSampleIdError(sampleIdValidation.error.issues[0].message);
      return;
    }

    // Validate device brand
    const deviceBrandValidation =
      deviceIdValidationSchema.safeParse(deviceBrandId);
    if (!deviceBrandValidation.success) {
      setDeviceBrandError(deviceBrandValidation.error.issues[0].message);
      return;
    }

    // Validate device model
    const deviceModelValidation =
      deviceIdValidationSchema.safeParse(deviceModelId);
    if (!deviceModelValidation.success) {
      setDeviceModelError(deviceModelValidation.error.issues[0].message);
      return;
    }

    // Validate device lens
    const deviceLensValidation =
      deviceIdValidationSchema.safeParse(deviceLensId);
    if (!deviceLensValidation.success) {
      setDeviceLensError(deviceLensValidation.error.issues[0].message);
      return;
    }

    // Validate magnification
    const magnificationValidation =
      magnificationSchema.safeParse(magnification);
    if (!magnificationValidation.success) {
      setMagnificationError(magnificationValidation.error.issues[0].message);
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
            family: family,
            genus: genus,
            species: species,
            nameCode: nameCode,
            trayCode: trayCode,
            sampleId: sampleId,
            deviceBrandId: deviceBrandId,
            deviceModelId: deviceModelId,
            deviceLensId: deviceLensId,
            magnification: magnification,
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
    fileStatus,
    files,
    msalInstance,
    sessionId,
    uploading,
    uuid,
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

            <Autocomplete
              id="input-family"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Family"
                  error={!!familyError}
                  helperText={familyError}
                />
              )}
              options={availableFamilies}
              value={family}
              onChange={(_event, newValue) => {
                setFamily(newValue || "");
                if (familyError) setFamilyError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              disabled={uploading}
            />

            <Autocomplete
              id="input-genus"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Genus"
                  error={!!genusError}
                  helperText={genusError}
                />
              )}
              options={availableGenera}
              value={genus}
              onChange={(_event, newValue) => {
                setGenus(newValue || "");
                if (genusError) setGenusError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              disabled={uploading}
            />

            <Autocomplete
              id="input-species"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Species"
                  error={!!speciesError}
                  helperText={speciesError}
                />
              )}
              options={availableSpecies}
              value={species}
              onChange={(_event, newValue) => {
                handleSpeciesChange(newValue || "");
                if (speciesError) setSpeciesError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              disabled={uploading}
            />

            <Autocomplete
              id="input-name-code"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Name Code"
                  error={!!nameCodeError}
                  helperText={nameCodeError}
                />
              )}
              options={availableNameCodes}
              value={nameCode}
              onChange={(_event, newValue) => {
                handleNameCodeChange(newValue || "");
                if (nameCodeError) setNameCodeError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              disabled={uploading}
            />

            <TextField
              id="input-tray-code"
              label="Tray Code"
              variant="outlined"
              select
              value={trayCode}
              onChange={(e) => {
                setTrayCode(e.target.value);
                if (trayCodeError) setTrayCodeError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              error={!!trayCodeError}
              helperText={trayCodeError}
              disabled={uploading}
            >
              <MenuItem value="">
                <em>Select Tray Code</em>
              </MenuItem>
              <MenuItem value="A">A</MenuItem>
              <MenuItem value="B">B</MenuItem>
              <MenuItem value="C">C</MenuItem>
              <MenuItem value="D">D</MenuItem>
              <MenuItem value="E">E</MenuItem>
            </TextField>

            <TextField
              id="input-magnification"
              label="Magnification"
              variant="outlined"
              type="number"
              value={magnification > 0 ? magnification : ""}
              onChange={(e) => {
                setMagnification(parseFloat(e.target.value) || 0);
                if (magnificationError) setMagnificationError("");
              }}
              sx={{
                marginTop: "10px",
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
              label="Sample ID"
              variant="outlined"
              value={sampleId}
              onChange={(e) => {
                setSampleId(e.target.value);
                if (sampleIdError) setSampleIdError("");
              }}
              sx={{
                marginTop: "10px",
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
              onBrandChange={setDeviceBrandId}
              onModelChange={setDeviceModelId}
              onLensChange={setDeviceLensId}
              devicesData={devicesData}
              disabled={uploading}
              brandError={deviceBrandError}
              modelError={deviceModelError}
              lensError={deviceLensError}
            />

            <TextField
              id="input-folder-name"
              label="Folder Name"
              variant="outlined"
              value={folderName}
              onChange={(e) => {
                setFolderName(e.target.value);
                folderNameManuallyEdited.current = true;
                if (folderNameError) setFolderNameError("");
              }}
              sx={{
                marginTop: "10px",
                width: "100%",
              }}
              error={!!folderNameError}
              helperText={folderNameError}
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
