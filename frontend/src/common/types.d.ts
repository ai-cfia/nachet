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
export interface Images {
  index: number;
  imageId?: number; // TODO convert to required once backend is implemented
  src: string;
  scores: number[];
  classifications: string[];
  boxes: InferenceBox[];
  annotated: boolean;
  imageDims: number[];
  overlapping: boolean[];
  overlappingIndices: number[];
  topN: Array<Array<{ score: number; label: string }>>;
}

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
  default?: boolean;
}

export interface BatchUploadMetadata {
  containerName: string;
  uuid: string;
  family: string;
  genus: string;
  species: string;
  nameCode: string;
  trayCode: string; // A | B | C | D | E
  sampleId: string;
  deviceBrandId: string;
  deviceModelId: string;
  deviceLensId: string;
  magnification: number;
  imageDataUrl: string;
  sessionId: string;
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
}

interface AzureStorageDirectoryItemApi {
  id: string;
  name: string;
  folder_prefix: string;
  description: string | null;
  picture_count: number;
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

export interface WorkflowInfo {
  workflow_id: string;
  image_id: string;
  status: string;
  started_at: number;
  last_checked_at: number;
  error: string | null;
}
