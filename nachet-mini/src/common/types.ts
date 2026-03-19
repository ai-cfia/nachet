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
  bboxSource: "model" | "user";
}

export interface BoxCSS {
  minWidth: number;
  minHeight: number;
  maxWidth: number;
  maxHeight: number;
  left: number;
  top: number;
}

export interface InferenceResult {
  scores: number[];
  classifications: string[];
  boxes: InferenceBox[];
  topN: Array<Array<{ score: number; label: string }>>;
  overlapping: boolean[];
  overlappingIndices: number[];
  labelOccurrence: { [key: string]: number };
  totalBoxes: number;
  models: Array<{ name: string; version: string }>;
  completedAt: string;
  isActive: boolean;
  minBoxSize: number;
}

export type TrayCode = "A" | "B" | "C" | "D" | "E" | "None";

export interface DeviceBrand {
  id: string;
  name: string;
  models: { id: string; name: string }[];
  lenses: { id: string; name: string }[];
}

export interface ImageMetadata {
  imageName: string;
  deviceBrandId: string;
  deviceModelId: string;
  deviceLensId: string;
  trayCode: TrayCode | "";
  magnification: number;
  description: string;
}

export interface Images {
  index: number;
  src: string;
  imageDims: number[];
  metadata: ImageMetadata;
  sha256: string;
}

export interface LabelOccurrences {
  [label: string]: number;
}
