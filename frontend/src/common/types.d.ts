export interface ApiInferenceData {
  filename: string;
  imageId: string;
  inferenceId: string;
  boxes: Array<{
    topN: Array<{ score: number; label: string }>;
    score: number;
    label: string;
    classId: string;
    objectTypeId: string;
    boxId: string;
    box: BoxCoordinates;
    overlapping: boolean;
    overlappingIndices: number;
    isVerified?: boolean;
  }>;
  labelOccurrence: {
    [key: string]: number;
  };
  totalBoxes: number;
  models: Array<{ name: string; version: string }>;
}

/**
 * Shared device and sample metadata fields
 * Base interface used by both ImageMetadata and BatchUploadMetadata
 */
export interface DeviceAndSampleMetadata {
  deviceBrandId: string;
  deviceModelId: string;
  deviceLensId: string;
  trayCode: string;
  magnification: number;
}

/**
 * Shared metadata fields for images
 * Used across frontend state, API requests, and validation
 */
export interface ImageMetadata extends DeviceAndSampleMetadata {
  imageName: string;
  imageDescription: string;
  imageDims: number[];
}

/**
 * Complete inference result for a single workflow execution
 * Stored separately from Images to support multiple inferences per image
 */
export interface InferenceResult {
  // Identifiers
  workflowId: string;
  imageId: string;
  inferenceId: string;
  pipelineId: string;
  pipelineName: string; // For display (e.g., "Swin transformer")

  // Inference data (from ApiInferenceData)
  scores: number[];
  classifications: string[];
  boxes: InferenceBox[];
  topN: Array<Array<{ score: number; label: string }>>;
  overlapping: boolean[];
  overlappingIndices: number[];
  labelOccurrence: { [key: string]: number };
  totalBoxes: number;
  models: Array<{ name: string; version: string }>;

  // Metadata
  completedAt: string; // ISO timestamp
  isActive: boolean; // For tracking which result is currently displayed
}

export interface Images extends Omit<Partial<ImageMetadata>, "imageDims"> {
  // Core fields
  index: number;
  imageId?: string; // Image ID from backend (UUID string)
  src: string;
  imageDims: number[]; // Required - always set when image is loaded

  // Workflow tracking - supports multiple inferences
  workflowIds: string[]; // Array of workflow_ids that have completed
  activeWorkflowId: string | null; // Which inference is currently displayed
}

/**
 * Helper type for Images that have been merged with InferenceResult data
 * Used in components and utilities that need both image and inference data
 */
export type ImageWithInference = Images & {
  annotated: boolean;
  scores: number[];
  classifications: string[];
  boxes: InferenceBox[];
  topN: Array<Array<{ score: number; label: string }>>;
  overlapping: boolean[];
  overlappingIndices: number[];
};

export interface BoxCoordinates {
  topX: number;
  topY: number;
  bottomX: number;
  bottomY: number;
}

export interface InferenceBox extends BoxCoordinates {
  inferenceId: string;
  boxId: string;
  classId: string;
  label: string;
  isVerified: boolean;
}

export interface BoxCSS {
  minWidth: number;
  minHeight: number;
  maxWidth: number;
  maxHeight: number;
  left: number;
  top: number;
}

interface FeedbackData {
  userId: string;
  inferenceId: string;
}

export interface FeedbackDataPositive extends FeedbackData {
  boxes: Array<{
    boxId: string;
  }>;
}

export interface FeedbackDataNegative extends FeedbackData {
  boxes: Array<{
    label: string;
    classId: string;
    boxId: string;
    box: BoxCoordinates;
    comment: string;
    family: string;
    genus: string;
    species: string;
    nameCode: string;
  }>;
}

export interface LabelOccurrences {
  [label: string]: number;
}

export interface SpeciesData {
  id?: number;
  label?: string;
  seedId: string;
  nameCode: string;
  family: string;
  genus: string;
  species: string;
  seedMetadata?: Record<string, any> | null;
}

export interface ApiSpeciesData {
  seeds: SpeciesData[];
}

export interface ModelMetadata {
  createdBy: string;
  creationDate: string;
  dataset: string;
  description: string;
  identifiable: string[];
  jobName: string;
  metrics: string[];
  modelName: string;
  models: string[];
  pipelineName: string;
  pipelineId: string;
  version?: string;
  default?: boolean;
}

export interface BatchUploadMetadata extends DeviceAndSampleMetadata {
  sessionId: string;
  seedId: string;
  sampleIdPrefix: string;
  sampleDescription?: string;
  imageDataUrl: string;
}

export interface BatchUploadImageResponse {
  workflowId: string;
  pictureId: string;
}

export interface BatchUploadInitRequest {
  folderId: string;
  fileCount: number;
}

export interface BatchUploadInitResponse {
  sessionId: string;
}

export interface CreateOrGetFolderRequest {
  normalizedPath: string;
  description?: string;
}

export interface CreateOrGetFolderResponse {
  folderId: string;
}

export interface UpdateFolderRequest {
  name?: string;
  description?: string;
}

export interface UpdateFolderResponse {
  id: string;
  message: string;
}

interface DirectoryPicture {
  inferenceExists: boolean;
  isValidation: boolean;
  pictureId: string;
}

interface AzureStorageDirectoryItem {
  folderId: string;
  folderName: string;
  folderPrefix: string;
  description: string | null;
  pictureCount: number;
  isDefaultFolder?: boolean;
}

interface AzureStorageDirectoryItemApi {
  id: string;
  name: string;
  folderPrefix: string;
  description: string | null;
  pictureCount: number;
  isDefaultFolder?: boolean;
  // pictures: DirectoryPictureApi[];
}
//   folderName: string;
//   nbPictures: number;
//   pictureSetId: string;
//   pictures: {
//     inferenceExists: boolean;
//     isValidation: boolean;
//     pictureId: string;
//   }[];
// }

interface ReadAzureStorageDirApi {
  directories: AzureStorageDirectoryItemApi[];
}

export interface DeviceBrand {
  id: string;
  name: string;
  description: string;
}

export interface DeviceModel {
  id: string;
  name: string;
  description: string;
}

export interface DeviceLens {
  id: string;
  name: string;
  description: string;
}

export interface ApiDeviceBrand {
  id: string;
  name: string;
  description: string;
  models: DeviceModel[];
  lenses: DeviceLens[];
}

export interface ApiDevicesResponse {
  devices: ApiDeviceBrand[];
}

// Workflow tracking types
export interface ImageSubmissionResponse {
  imageId: string;
  workflowId: string;
  status: string;
  message: string;
}

export interface ParentWorkflowStatus {
  workflowId: string;
  status: string;
  progressPercentage: number;
  createdAt: string | null;
  completedAt: string | null;
  failedAt: string | null;
  errorMessage: string | null;
  malwareDetected: boolean | null;
}

export interface ProcessingWorkflowStatus {
  status: string;
  stages: {
    uploaded: boolean;
    defenderScanning: boolean;
    defenderScanned: boolean;
    sanitizing: boolean;
    sanitized: boolean;
  };
  timestamps: {
    uploadedAt: string | null;
    defenderScanStartedAt: string | null;
    defenderScanCompletedAt: string | null;
    sanitizationStartedAt: string | null;
    sanitizationCompletedAt: string | null;
    completedAt: string | null;
    failedAt: string | null;
  };
  defenderScanResult: {
    status: string;
    tags: Record<string, any>;
    scanTimestamp: string;
  } | null;
  blobUrls: {
    original: string | null;
    sanitized: string | null;
  };
  errorMessage: string | null;
  errorDetails: any | null;
}

export interface InferenceWorkflowStatus {
  workflowId: string;
  status: string;
  pipelineId: string;
  createdAt: string | null;
  startedAt: string | null;
  completedAt: string | null;
  failedAt: string | null;
  errorMessage: string | null;
  requestPayload: any;
}

export interface WorkflowStatusResponse {
  workflowId: string;
  workflowType: string;
  imageId: string;
  overallStatus: string;
  parentWorkflow: ParentWorkflowStatus | null;
  processingWorkflow: ProcessingWorkflowStatus | null;
  inferenceWorkflow: InferenceWorkflowStatus | null;
  authorization: {
    userId: string;
    isOwner: boolean;
    isCfiaAdmin: boolean;
  };
}

export type WorkflowStatus =
  | "queued" // Waiting in queue (not yet submitted to backend)
  | "pending" // Submitted to backend, waiting to process
  | "processing" // Active processing
  | "completed" // Successfully completed
  | "failed" // Error occurred
  | "cancelled"; // User cancelled (future)

export interface WorkflowInfo {
  workflowId: string;
  imageId: string;
  imageIndex: number; // Track which image this workflow belongs to
  pipelineId: string; // Which model/pipeline is running
  pipelineName: string; // Display name for UI
  status: WorkflowStatus;
  startedAt: number;
  lastCheckedAt: number;
  error: string | null;
  queuePosition?: number; // Position in queue (for queued items)
}
