export interface ExportManifest {
  version: "1.0";
  exportedAt: string;
  application: "nachet-mini";
  images: ExportImageEntry[];
}

export interface ExportImageEntry {
  fileName: string;
  fileSha256: string;
  metadata: {
    imageName: string;
    deviceBrandId: string;
    deviceModelId: string;
    deviceLensId: string;
    trayCode: string;
    description: string;
  };
  dimensions: { width: number; height: number };
  inferenceResults: ExportInferenceEntry[];
}

export interface ExportInferenceEntry {
  modelConfigId: string;
  isEdited: boolean;
  completedAt: string;
  models: Array<{ name: string; version: string }>;
  totalBoxes: number;
  labelOccurrence: Record<string, number>;
  boxes: ExportBoxEntry[];
}

export interface ExportBoxEntry {
  boxId: string;
  label: string;
  classId: string;
  score: number;
  bboxSource: "model" | "user";
  isVerified: boolean;
  coordinates: {
    topX: number;
    topY: number;
    bottomX: number;
    bottomY: number;
  };
  topNClassifications: Array<{ score: number; label: string }>;
}
