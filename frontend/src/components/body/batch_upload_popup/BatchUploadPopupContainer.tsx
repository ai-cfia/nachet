import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";
import { batchUploadInit, createOrGetFolder } from "@common/api";
import { validateImageFile } from "@common";
import { BatchUploadMetadata } from "@common/types";
import {
  useSpeciesData,
  useDeviceData,
  useZodFieldValidation,
  ERROR_KEY_MAPPINGS,
} from "@hooks";
import { getSeedIdByTaxonomy } from "../../../utils/seedLookup";
import {
  folderNameSchema,
  magnificationSchema,
  trayCodeSchema,
  taxonomicFieldSchema,
  sampleIdSchema,
  deviceIdValidationSchema,
  fileListSchema,
  descriptionSchema,
} from "@common/validation";
import { getZodErrorKey } from "@common/zodErrorMap";
import { BatchUploadQueueManager } from "../../../services/BatchUploadQueueManager";
import { useBatchUploadStore } from "@stores/useBatchUploadStore";
import { useModalStore } from "@stores/useModalStore";
import { BatchUploadPopupView } from "./BatchUploadPopupView";
import { useTranslation } from "react-i18next";
import { useNotificationStore } from "@stores/useNotificationStore";
import { useNachetAuth } from "@auth";

interface BatchUploadPopupContainerProps {
  backendUrl: string;
  containerName: string;
  uuid: string;
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
}

export const BatchUploadPopupContainer = (
  props: BatchUploadPopupContainerProps,
) => {
  const { backendUrl, setReadAzureStorage } = props;
  const { closeBatchUploadPopup } = useModalStore();
  const { t } = useTranslation("validation");
  const { t: tErrors } = useTranslation("errors");
  const { addError, addWarning } = useNotificationStore();

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
  const [sampleIdPrefix, setSampleIdPrefix] = useState<string>("");
  const [sampleDescription, setSampleDescription] = useState<string>("");
  const [folderDescription, setFolderDescription] = useState<string>("");
  const [deviceBrandId, setDeviceBrandId] = useState<string>("");
  const [deviceModelId, setDeviceModelId] = useState<string>("");
  const [deviceLensId, setDeviceLensId] = useState<string>("");
  const [magnification, setMagnification] = useState<number>(1);

  // Track if user has manually edited folder name
  const folderNameManuallyEdited = useRef<boolean>(false);

  // Validation error states
  const [folderNameError, setFolderNameError] = useState<string>("");
  const [familyError, setFamilyError] = useState<string>("");
  const [genusError, setGenusError] = useState<string>("");
  const [speciesError, setSpeciesError] = useState<string>("");
  const [nameCodeError, setNameCodeError] = useState<string>("");
  const [trayCodeError, setTrayCodeError] = useState<string>("");
  const [sampleIdPrefixError, setSampleIdPrefixError] = useState<string>("");
  const [sampleDescriptionError, setSampleDescriptionError] =
    useState<string>("");
  const [deviceBrandError, setDeviceBrandError] = useState<string>("");
  const [deviceModelError, setDeviceModelError] = useState<string>("");
  const [deviceLensError, setDeviceLensError] = useState<string>("");
  const [magnificationError, setMagnificationError] = useState<string>("");
  const [filesError, setFilesError] = useState<string>("");
  const [folderDescriptionError, setFolderDescriptionError] =
    useState<string>("");

  // Zod validation hooks for auto-normalization on blur
  const folderDescriptionValidation = useZodFieldValidation(
    descriptionSchema,
    folderDescription,
    setFolderDescription,
    setFolderDescriptionError,
    ERROR_KEY_MAPPINGS.description,
  );

  const sampleDescriptionValidation = useZodFieldValidation(
    descriptionSchema,
    sampleDescription,
    setSampleDescription,
    setSampleDescriptionError,
    ERROR_KEY_MAPPINGS.description,
  );

  const { speciesData } = useSpeciesData(backendUrl);
  const { devicesData } = useDeviceData(backendUrl);
  const { isAuthenticated, isLoading: authLoading } = useNachetAuth();

  // Folder creation state
  const [createdFolderId, setCreatedFolderId] = useState<string>("");
  const [creatingFolder, setCreatingFolder] = useState<boolean>(false);

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

    if (authLoading || !isAuthenticated) {
      console.warn("Authentication in progress or user not authenticated");
      return;
    }

    // Validate description using descriptionSchema (consistent with other description fields)
    const descriptionValidationResult =
      descriptionSchema.safeParse(folderDescription);
    if (!descriptionValidationResult.success) {
      const issue = descriptionValidationResult.error.issues[0];
      if (issue.code === "too_small") {
        setFolderDescriptionError(t("description.empty"));
      } else if (issue.code === "too_big") {
        setFolderDescriptionError(t("description.tooLong"));
      } else {
        setFolderDescriptionError(
          t(getZodErrorKey(descriptionValidationResult.error)),
        );
      }
      return;
    }

    setCreatingFolder(true);
    setUploadError(null);
    setFolderDescriptionError("");

    try {
      const result = await createOrGetFolder({
        backendUrl,
        normalizedPath: normalizedFolderName,
        description: descriptionValidationResult.data,
      });

      setCreatedFolderId(result.folderId);
      console.log(`Folder created/retrieved: ${result.folderId}`);
      // Trigger directory list refresh
      setReadAzureStorage((prev) => !prev);
    } catch (error) {
      console.error(
        "Folder creation failed:",
        error instanceof Error ? error.message : String(error),
      );
      setUploadError(
        error instanceof Error
          ? error.message
          : "Failed to create folder. Please try again.",
      );
    } finally {
      setCreatingFolder(false);
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
      // Validate each file and separate valid from invalid
      const validFiles: File[] = [];
      const rejectedFiles: { name: string; reasons: string[] }[] = [];

      for (let i = 0; i < selectedFiles.length; i++) {
        const file = selectedFiles[i];
        const fileValidation = await validateImageFile(file);

        if (fileValidation.isValid) {
          validFiles.push(file);
        } else {
          rejectedFiles.push({
            name: file.name,
            reasons: fileValidation.errors,
          });
        }
      }

      // Handle case where all files are invalid
      if (validFiles.length === 0) {
        const errorMessages = rejectedFiles.map(
          (f) => `${f.name}: ${f.reasons.join(", ")}`,
        );
        setFilesError(
          `All files failed validation:\n${errorMessages.join("\n")}`,
        );
        addError("All selected files failed validation", "batch-upload");
        return;
      }

      // Convert validFiles array to FileList using DataTransfer API
      const dataTransfer = new DataTransfer();
      validFiles.forEach((file) => dataTransfer.items.add(file));
      const validFileList = dataTransfer.files;

      // Validate the valid files (e.g., max 100 files)
      const validationResult = fileListSchema.safeParse(validFileList);
      if (!validationResult.success) {
        setFilesError(validationResult.error.issues[0].message);
        return;
      }

      // Show warning if some files were rejected
      if (rejectedFiles.length > 0) {
        // Categorize rejection reasons
        const sizeErrors = rejectedFiles.filter((f) =>
          f.reasons.some((r) => r.includes("10MB")),
        ).length;
        const typeErrors = rejectedFiles.filter((f) =>
          f.reasons.some((r) => r.includes("PNG")),
        ).length;
        const dimensionErrors = rejectedFiles.filter((f) =>
          f.reasons.some((r) => r.includes("1920x1080")),
        ).length;

        const errorParts: string[] = [];
        if (sizeErrors > 0) errorParts.push(`${sizeErrors} too large`);
        if (typeErrors > 0) errorParts.push(`${typeErrors} wrong format`);
        if (dimensionErrors > 0)
          errorParts.push(`${dimensionErrors} dimensions too large`);

        const message = `${rejectedFiles.length} file(s) excluded: ${errorParts.join(", ")}. ${validFiles.length} file(s) will be uploaded.`;
        addWarning(message, 8000);
      }

      // Clear any previous errors and set valid files
      setFilesError("");
      setFiles(validFileList);
      setFileCount(validFiles.length);
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
    setSampleIdPrefix("");
    // Reset device fields to empty strings
    setDeviceBrandId("");
    setDeviceModelId("");
    setDeviceLensId("");
    setMagnification(1);
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
      setUploadError(tErrors("auth.signInRequiredUpload"));
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
    setSampleIdPrefixError("");
    setDeviceBrandError("");
    setDeviceModelError("");
    setDeviceLensError("");
    setMagnificationError("");
    setFilesError("");

    // Validate folder name
    const folderValidation = folderNameSchema.safeParse(folderName);
    if (!folderValidation.success) {
      setFolderNameError(t(getZodErrorKey(folderValidation.error)));
      return;
    }

    // Validate family
    const familyValidation = taxonomicFieldSchema.safeParse(family);
    if (!familyValidation.success) {
      setFamilyError(t(getZodErrorKey(familyValidation.error)));
      return;
    }

    // Validate genus
    const genusValidation = taxonomicFieldSchema.safeParse(genus);
    if (!genusValidation.success) {
      setGenusError(t(getZodErrorKey(genusValidation.error)));
      return;
    }

    // Validate species
    const speciesValidation = taxonomicFieldSchema.safeParse(species);
    if (!speciesValidation.success) {
      setSpeciesError(t(getZodErrorKey(speciesValidation.error)));
      return;
    }

    // Validate name code
    const nameCodeValidation = taxonomicFieldSchema.safeParse(nameCode);
    if (!nameCodeValidation.success) {
      setNameCodeError(t(getZodErrorKey(nameCodeValidation.error)));
      return;
    }

    // Validate tray code
    const trayCodeValidation = trayCodeSchema.safeParse(trayCode);
    if (!trayCodeValidation.success) {
      setTrayCodeError(t(getZodErrorKey(trayCodeValidation.error)));
      return;
    }

    // Validate sample ID prefix
    const sampleIdPrefixValidation = sampleIdSchema.safeParse(sampleIdPrefix);
    if (!sampleIdPrefixValidation.success) {
      setSampleIdPrefixError(t(getZodErrorKey(sampleIdPrefixValidation.error)));
      return;
    }

    // Validate sample description (optional, but if provided must be valid)
    if (sampleDescription && sampleDescription.trim() !== "") {
      const sampleDescriptionValidation =
        descriptionSchema.safeParse(sampleDescription);
      if (!sampleDescriptionValidation.success) {
        const issue = sampleDescriptionValidation.error.issues[0];
        if (issue.code === "too_small") {
          setSampleDescriptionError(t("description.empty"));
        } else if (issue.code === "too_big") {
          setSampleDescriptionError(t("description.tooLong"));
        } else {
          setSampleDescriptionError(
            t(getZodErrorKey(sampleDescriptionValidation.error)),
          );
        }
        return;
      }
    }

    // Validate device brand
    console.log("DEBUG: deviceBrandId value:", deviceBrandId);
    console.log("DEBUG: deviceBrandId type:", typeof deviceBrandId);
    console.log("DEBUG: deviceBrandId length:", deviceBrandId?.length);

    if (!deviceBrandId || deviceBrandId === "") {
      setDeviceBrandError(t("deviceId.empty"));
      return;
    }
    const deviceBrandValidation =
      deviceIdValidationSchema.safeParse(deviceBrandId);
    if (!deviceBrandValidation.success) {
      console.log(
        "DEBUG: deviceBrandValidation error:",
        deviceBrandValidation.error,
      );
      setDeviceBrandError(t(getZodErrorKey(deviceBrandValidation.error)));
      return;
    }

    // Validate device model
    if (!deviceModelId || deviceModelId === "") {
      setDeviceModelError(t("deviceId.empty"));
      return;
    }
    const deviceModelValidation =
      deviceIdValidationSchema.safeParse(deviceModelId);
    if (!deviceModelValidation.success) {
      setDeviceModelError(t(getZodErrorKey(deviceModelValidation.error)));
      return;
    }

    // Validate device lens
    if (!deviceLensId || deviceLensId === "") {
      setDeviceLensError(t("deviceId.empty"));
      return;
    }
    const deviceLensValidation =
      deviceIdValidationSchema.safeParse(deviceLensId);
    if (!deviceLensValidation.success) {
      setDeviceLensError(t(getZodErrorKey(deviceLensValidation.error)));
      return;
    }

    // Validate magnification
    const magnificationValidation =
      magnificationSchema.safeParse(magnification);
    if (!magnificationValidation.success) {
      setMagnificationError(t(getZodErrorKey(magnificationValidation.error)));
      return;
    }

    // Validate files
    if (files == null) {
      setFilesError(t("file.noneSelected"));
      return;
    }
    const filesValidation = fileListSchema.safeParse(files);
    if (!filesValidation.success) {
      setFilesError(t(getZodErrorKey(filesValidation.error)));
      return;
    }

    if (authLoading) {
      addWarning(tErrors("auth.inProgress"), 8000);
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
    batchUploadInit({
      backendUrl,
      folderId: createdFolderId,
      fileCount,
    })
      .then(({ sessionId }) => {
        // Create session in Zustand store
        createSession(sessionId, fileCount);

        // Configure queue manager
        queueManagerRef.current.configure({
          backendUrl,
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
            console.error(`Upload failed: ${file.name} - ${error.message}`);
            // Add error to notification log with file name and error message
            addError(`${file.name}: ${error.message}`, "batch-upload");
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
              sampleIdPrefix,
              sampleDescription,
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
    closeBatchUploadPopup();
  };

  // Cleanup on unmount
  useEffect(() => {
    const queueManager = queueManagerRef.current;
    return () => {
      queueManager.clear();
    };
  }, []);

  // Prepare props for the View component
  const viewProps = {
    // Dialog control
    onClose: handleClose,

    // Upload state
    uploading,
    uploadError,
    uploadSuccess,
    uploadProgress,

    // Form field values
    files,
    fileCount,
    folderName,
    folderDescription,
    family,
    genus,
    species,
    nameCode,
    trayCode,
    sampleIdPrefix,
    sampleDescription,
    deviceBrandId,
    deviceModelId,
    deviceLensId,
    magnification,

    // Form field change handlers
    onFilesSelected: handleFilesSelected,
    onFolderNameChange: (value: string) => {
      setFolderName(value);
      folderNameManuallyEdited.current = true;
      if (folderNameError) setFolderNameError("");
      // Reset created folder ID when folder name changes
      if (createdFolderId) setCreatedFolderId("");
    },
    onFolderDescriptionChange: folderDescriptionValidation.onChange,
    onFolderDescriptionBlur: folderDescriptionValidation.onBlur,
    onFamilyChange: (value: string) => {
      setFamily(value);
      if (familyError) setFamilyError("");
    },
    onGenusChange: (value: string) => {
      setGenus(value);
      if (genusError) setGenusError("");
    },
    onSpeciesChange: (value: string) => {
      setSpecies(value);
      if (speciesError) setSpeciesError("");
    },
    onNameCodeChange: (value: string) => {
      setNameCode(value);
      if (nameCodeError) setNameCodeError("");
    },
    onTrayCodeChange: (value: string) => {
      setTrayCode(value);
      if (trayCodeError) setTrayCodeError("");
    },
    onSampleIdPrefixChange: (value: string) => {
      setSampleIdPrefix(value);
      if (sampleIdPrefixError) setSampleIdPrefixError("");
    },
    onSampleDescriptionChange: sampleDescriptionValidation.onChange,
    onSampleDescriptionBlur: sampleDescriptionValidation.onBlur,
    onDeviceBrandChange: setDeviceBrandId,
    onDeviceModelChange: setDeviceModelId,
    onDeviceLensChange: setDeviceLensId,
    onMagnificationChange: (value: number) => {
      setMagnification(value);
      if (magnificationError) setMagnificationError("");
    },

    // Validation errors
    folderNameError,
    folderDescriptionError,
    familyError,
    genusError,
    speciesError,
    nameCodeError,
    trayCodeError,
    sampleIdPrefixError,
    sampleDescriptionError,
    deviceBrandError,
    deviceModelError,
    deviceLensError,
    magnificationError,
    filesError,

    // Action handlers
    onCreateFolder: handleCreateFolder,
    onUpload: handleUpload,

    // Folder creation state
    createdFolderId,
    creatingFolder,

    // Data from API
    speciesData: speciesData?.seeds || [],
    devicesData,

    // Upload session state
    currentSession,
    uploads,
  };

  return <BatchUploadPopupView {...viewProps} />;
};

export default BatchUploadPopupContainer;
