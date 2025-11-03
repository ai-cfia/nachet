export interface ApiInferenceData {
  filename: string;
  imageId: string;
  inference_id: string;
  boxes: Array<{
    topN: Array<{ score: number; label: string }>;
    score: number;
    label: string;
    classId: string;
    object_type_id: string;
    box_id: string;
    box: BoxCoordinates;
    overlapping: boolean;
    overlappingIndices: number;
    is_verified?: boolean;
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
  workflow_id: string;
  image_id: string;
  inference_id: string;
  pipeline_id: string;
  pipeline_name: string; // For display (e.g., "Swin transformer")

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
  completed_at: string; // ISO timestamp
  is_active: boolean; // For tracking which result is currently displayed
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
  is_verified: boolean;
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
    name_code: string;
  }>;
}

export interface LabelOccurrences {
  [label: string]: number;
}

export interface SpeciesData {
  id?: number;
  label?: string;
  seed_id: string;
  name_code: string;
  family: string;
  genus: string;
  species: string;
}

export interface ApiSpeciesData {
  seeds: SpeciesData[];
}

export interface ModelMetadata {
  created_by: string;
  creation_date: string;
  dataset: string;
  description: string;
  identifiable: string[];
  job_name: string;
  metrics: string[];
  model_name: string;
  models: string[];
  pipeline_name: string;
  pipeline_id: string;
  version?: string;
  default?: boolean;
}

export interface BatchUploadMetadata extends DeviceAndSampleMetadata {
  sessionId: string;
  seedId: string;
  sampleIdPrefix: string;
  imageDataUrl: string;
}

export interface BatchUploadImageResponse {
  workflow_id: string;
  picture_id: string;
}

export interface BatchUploadInitRequest {
  folder_id: string;
  file_count: number;
}

export interface BatchUploadInitResponse {
  session_id: string;
}

export interface CreateOrGetFolderRequest {
  normalized_path: string;
  description?: string;
}

export interface CreateOrGetFolderResponse {
  folder_id: string;
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
  folder_prefix: string;
  description: string | null;
  picture_count: number;
  is_default_folder?: boolean;
  // pictures: DirectoryPictureApi[];
}
//   folder_name: string;
//   nb_pictures: number;
//   picture_set_id: string;
//   pictures: {
//     inference_exists: boolean;
//     is_validation: boolean;
//     picture_id: string;
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
  image_id: string;
  workflow_id: string;
  status: string;
  message: string;
}

export interface ParentWorkflowStatus {
  workflow_id: string;
  status: string;
  progress_percentage: number;
  created_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  malware_detected: boolean | null;
}

export interface ProcessingWorkflowStatus {
  status: string;
  stages: {
    uploaded: boolean;
    defender_scanning: boolean;
    defender_scanned: boolean;
    sanitizing: boolean;
    sanitized: boolean;
  };
  timestamps: {
    uploaded_at: string | null;
    defender_scan_started_at: string | null;
    defender_scan_completed_at: string | null;
    sanitization_started_at: string | null;
    sanitization_completed_at: string | null;
    completed_at: string | null;
    failed_at: string | null;
  };
  defender_scan_result: {
    status: string;
    tags: Record<string, any>;
    scan_timestamp: string;
  } | null;
  blob_urls: {
    original: string | null;
    sanitized: string | null;
  };
  error_message: string | null;
  error_details: any | null;
}

export interface InferenceWorkflowStatus {
  workflow_id: string;
  status: string;
  pipeline_id: string;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  request_payload: any;
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  workflow_type: string;
  image_id: string;
  overall_status: string;
  parent_workflow: ParentWorkflowStatus | null;
  processing_workflow: ProcessingWorkflowStatus | null;
  inference_workflow: InferenceWorkflowStatus | null;
  authorization: {
    user_id: string;
    is_owner: boolean;
    is_cfia_admin: boolean;
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
  workflow_id: string;
  image_id: string;
  imageIndex: number; // Track which image this workflow belongs to
  pipeline_id: string; // Which model/pipeline is running
  pipeline_name: string; // Display name for UI
  status: WorkflowStatus;
  started_at: number;
  last_checked_at: number;
  error: string | null;
  queuePosition?: number; // Position in queue (for queued items)
}
