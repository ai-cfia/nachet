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

export interface Images {
  index: number;
  src: string;
  imageDims: number[];
}

export interface LabelOccurrences {
  [label: string]: number;
}
