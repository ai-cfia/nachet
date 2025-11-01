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
import { batchUploadInit, createOrGetFolder } from "@common/api";
import { validateImageFile } from "@common";
import { BatchUploadMetadata } from "@common/types";
import { useSpeciesData, useDeviceData } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { getSeedIdByTaxonomy } from "../../../utils/seedLookup";
import {
  folderNameSchema,
  magnificationSchema,
  trayCodeSchema,
  taxonomicFieldSchema,
  sampleIdSchema,
  deviceIdValidationSchema,
  fileListSchema,
  safeUserInputSchema,
} from "@common/validation";
import { DeviceSelectionFields } from "@components/common/DeviceSelectionFields";
import { BatchUploadQueueManager } from "../../../services/BatchUploadQueueManager";
import { useBatchUploadStore } from "@stores/useBatchUploadStore";

interface params {
  setBatchUploadOpen: Dispatch<SetStateAction<boolean>>;
  backendUrl: string;
  containerName: string;
  uuid: string;
  apiScopeClaim: string;
}

const BatchUploadPopup = (props: params) => {
  const { setBatchUploadOpen, backendUrl, apiScopeClaim } = props;

  const [files, setFiles] = useState<FileList | null>(null);
  const [fileCount, setFileCount] = useState<number>(0);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Queue manager singleton - persists across renders
  const queueManagerRef = useRef<BatchUploadQueueManager>(
    new BatchUploadQueueManager(),
  );

  // Batch upload store for global state persistence
  const {
    currentSession,
    uploads,
    createSession,
    addUpload,
    updateUploadStatus,
    setUploadResult,
    removeUpload,
  } = useBatchUploadStore();

  // Computed status from Zustand store
  const uploadSuccess = useMemo(() => {
    if (!currentSession) return false;
    return (
      currentSession.status === "completed" && currentSession.failedFiles === 0
    );
  }, [currentSession]);

  const uploadProgress = useMemo(() => {
    if (!currentSession || currentSession.totalFiles === 0) return 0;
    return (
      ((currentSession.completedFiles + currentSession.failedFiles) /
        currentSession.totalFiles) *
      100
    );
  }, [currentSession]);

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
  const [folderDescriptionError, setFolderDescriptionError] =
    useState<string>("");

  const { speciesData } = useSpeciesData(backendUrl, apiScopeClaim);
  const { devicesData } = useDeviceData(backendUrl, apiScopeClaim);
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  // Folder creation state
  const [folderDescription, setFolderDescription] = useState<string>("");
  const [createdFolderId, setCreatedFolderId] = useState<string>("");
  const [creatingFolder, setCreatingFolder] = useState<boolean>(false);

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

  // Computed normalized folder name
  const normalizedFolderName = useMemo(() => {
    return folderName
      .toLowerCase()
      .replace(/[^a-z0-9/._-]/g, "-")
      .replace(/^\/+|\/+$/g, ""); // Remove leading/trailing slashes
  }, [folderName]);

  // Handle folder creation
  const handleCreateFolder = async () => {
    if (!folderName) {
      setFolderNameError("Folder name is required");
      return;
    }

    if (inProgress !== InteractionStatus.None || !isAuthenticated) {
      console.warn("Authentication in progress or user not authenticated");
      return;
    }

    // Validate description using safeUserInputSchema (same as CreateDirectoryPopup)
    const descriptionValidationResult =
      safeUserInputSchema.safeParse(folderDescription);
    if (!descriptionValidationResult.success) {
      setFolderDescriptionError(
        descriptionValidationResult.error.issues[0].message,
      );
      return;
    }

    setCreatingFolder(true);
    setUploadError(null);
    setFolderDescriptionError("");

    try {
      const accessToken = await acquireAccessToken(msalInstance, [
        apiScopeClaim,
      ]);
      const result = await createOrGetFolder({
        backendUrl,
        accessToken,
        normalizedPath: normalizedFolderName,
        description: descriptionValidationResult.data,
      });

      setCreatedFolderId(result.folder_id);
      console.log(`Folder created/retrieved: ${result.folder_id}`);
    } catch (error) {
      console.error("Folder creation failed:", error);
      setUploadError(
        error instanceof Error
          ? error.message
          : "Failed to create folder. Please try again.",
      );
    } finally {
      setCreatingFolder(false);
    }
  };

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

  // Auto-prefill folder name when both genus and species are set (only if not manually edited)
  useEffect(() => {
    if (suggestedFolderName && !folderNameManuallyEdited.current) {
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
    }
  };

  const resetUpload = (): void => {
    setUploading(false);
    setUploadError(null);
  };

  const resetForm = (): void => {
    setFolderName("");
    setFolderDescription("");
    setFamily("");
    setGenus("");
    setSpecies("");
    setNameCode("");
    setTrayCode("");
    setSampleId("");
    // Reset device fields to empty strings
    setDeviceBrandId("");
    setDeviceModelId("");
    setDeviceLensId("");
    setMagnification(0);
    setFiles(null);
    setFileCount(0);
    folderNameManuallyEdited.current = false;
    // Reset folder creation state
    setCreatedFolderId("");
    setFolderNameError("");
    setFolderDescriptionError("");
  };

  const handleUpload = (): void => {
    if (!isAuthenticated) {
      setUploadError("You must be signed in to upload files");
      return;
    }

    // Clear previous errors
    setUploadError(null);
    setFolderNameError("");
    setFolderDescriptionError("");
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
    console.log("DEBUG: deviceBrandId value:", deviceBrandId);
    console.log("DEBUG: deviceBrandId type:", typeof deviceBrandId);
    console.log("DEBUG: deviceBrandId length:", deviceBrandId?.length);

    if (!deviceBrandId || deviceBrandId === "") {
      setDeviceBrandError("Please select a device brand");
      return;
    }
    const deviceBrandValidation =
      deviceIdValidationSchema.safeParse(deviceBrandId);
    if (!deviceBrandValidation.success) {
      console.log(
        "DEBUG: deviceBrandValidation error:",
        deviceBrandValidation.error,
      );
      setDeviceBrandError("Please select a valid device brand");
      return;
    }

    // Validate device model
    if (!deviceModelId || deviceModelId === "") {
      setDeviceModelError("Please select a device model");
      return;
    }
    const deviceModelValidation =
      deviceIdValidationSchema.safeParse(deviceModelId);
    if (!deviceModelValidation.success) {
      setDeviceModelError("Please select a valid device model");
      return;
    }

    // Validate device lens
    if (!deviceLensId || deviceLensId === "") {
      setDeviceLensError("Please select a device lens");
      return;
    }
    const deviceLensValidation =
      deviceIdValidationSchema.safeParse(deviceLensId);
    if (!deviceLensValidation.success) {
      setDeviceLensError("Please select a valid device lens");
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

    // Validate folder creation (Phase 5.5)
    if (!createdFolderId) {
      setUploadError(
        "Please create a folder first by clicking 'Create Folder' button",
      );
      setUploading(false);
      return;
    }

    // Get seed_id from taxonomy
    let seedId: string;
    try {
      seedId = getSeedIdByTaxonomy({
        family,
        genus,
        species,
        nameCode,
      });
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : "Failed to lookup seed ID from taxonomy",
      );
      setUploading(false);
      return;
    }

    // Initialize batch upload session
    acquireAccessToken(msalInstance, [apiScopeClaim])
      .then((accessToken) => {
        return batchUploadInit({
          backendUrl,
          accessToken,
          folderId: createdFolderId,
          fileCount,
        }).then((response) => ({
          accessToken,
          sessionId: response.session_id,
        }));
      })
      .then(({ sessionId }) => {
        // Create session in Zustand store
        createSession(sessionId, fileCount);

        const scopes = apiScopeClaim ? [apiScopeClaim] : [];

        // Configure queue manager
        queueManagerRef.current.configure({
          backendUrl,
          msalInstance,
          scopes,
          uploadStore: {
            addUpload,
            updateUploadStatus,
            setUploadResult,
            removeUpload,
          },
          onComplete: (_workflowId, file, results) => {
            console.log(`Upload completed: ${file.name}`, results);
          },
          onError: (_workflowId, file, error) => {
            console.error(`Upload failed: ${file.name}`, error);
          },
        });

        // Enqueue all files
        if (files) {
          for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const metadata: Omit<BatchUploadMetadata, "imageDataUrl"> = {
              sessionId,
              seedId,
              trayCode,
              sampleId,
              deviceBrandId,
              deviceModelId,
              deviceLensId,
              magnification,
            };
            queueManagerRef.current.enqueue(file, metadata);
          }
        }
      })
      .catch((error) => {
        setUploadError(error.toString());
        setUploading(false);
      });
  };

  const handleClose = (): void => {
    // Note: Queue manager continues running even after modal closes
    // This allows uploads to complete in the background
    // The Zustand store persists the state, so progress can be resumed
    resetUpload();
    resetForm();
    setBatchUploadOpen(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    const queueManager = queueManagerRef.current;
    return () => {
      queueManager.clear();
    };
  }, []);

  return (
    <Dialog
      open={true}
      onClose={handleClose}
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
            Batch Upload Images
          </Typography>
          <IconButton onClick={handleClose} size="small">
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
                    // Reset created folder ID when folder name changes
                    if (createdFolderId) setCreatedFolderId("");
                  }}
                  sx={{
                    width: "100%",
                  }}
                  error={!!folderNameError}
                  helperText={
                    folderNameError ||
                    "Folder will be created at root level. Use letters, numbers, hyphens, and underscores."
                  }
                  disabled={uploading || creatingFolder}
                  placeholder="e.g., avena-fatua or mycology-samples"
                />

                <TextField
                  id="input-folder-description"
                  label="Description (Optional)"
                  variant="outlined"
                  value={folderDescription}
                  onChange={(e) => {
                    setFolderDescription(e.target.value);
                    if (folderDescriptionError) setFolderDescriptionError("");
                  }}
                  sx={{
                    width: "100%",
                  }}
                  multiline
                  rows={2}
                  error={!!folderDescriptionError}
                  helperText={
                    folderDescriptionError ||
                    "Optional description for this directory (max 500 characters)"
                  }
                  disabled={uploading || creatingFolder}
                  placeholder="e.g., Sample collection from field trial 2025"
                />

                {/* Create Folder Button */}
                <Button
                  variant="contained"
                  onClick={handleCreateFolder}
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
                    ? "Creating..."
                    : createdFolderId
                      ? "Folder Created"
                      : "Create Folder"}
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
                        Upload Status
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
                                ? `Error: ${uploadInfo.error}`
                                : status === "queued"
                                  ? `Queued (${uploadInfo?.queuePosition ?? ""})`
                                  : status === "processing"
                                    ? "Processing..."
                                    : status === "completed"
                                      ? "Completed"
                                      : status === "failed"
                                        ? "Failed"
                                        : "Pending"
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
            </Box>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default BatchUploadPopup;
