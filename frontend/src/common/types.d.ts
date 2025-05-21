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
    seed_name: number;
  };
  totalBoxes: number;
  models: Array<{ name: string; version: number }>;
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

interface ClassData {
  id: number;
  classId: string;
  label: string;
}

interface ApiSpeciesData {
  seeds: Array<{
    seed_id: string;
    seed_name: string;
  }>;
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
  default?: boolean;
}

export interface BatchUploadMetadata {
  containerName: string;
  uuid: string;
  seedId: string;
  seedName: string; // TODO: remove when backend is implemented
  zoom: number;
  seedCount: number;
  imageDataUrl: string;
  sessionId: string;
}

interface DirectoryPicture {
  inferenceExists: boolean;
  isValidation: boolean;
  pictureId: string;
}

interface AzureStorageDirectoryItem {
  folderName: string;
  nbPictures: number;
  pictureSetId: string;
  pictures: DirectoryPicture[];
}

interface AzureStorageDirectoryItemApi {
  folder_name: string;
  nb_pictures: number;
  picture_set_id: string;
  pictures: {
    inference_exists: boolean;
    is_validation: boolean;
    picture_id: string;
  }[];
}

interface ReadAzureStorageDirApi {
  folders: AzureStorageDirectoryItemApi[];
}
