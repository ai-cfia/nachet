import JSZip from "jszip";
import { saveAs } from "file-saver";
import type { Images, InferenceResult } from "@common/types";
import type {
  ExportManifest,
  ExportImageEntry,
  ExportInferenceEntry,
  ExportBoxEntry,
} from "@common/exportTypes";

interface ResultEntry {
  modelConfigId: string;
  result: InferenceResult;
}

/**
 * Build an ExportManifest from selected images and results.
 *
 * Selection logic:
 * - Image checked → export image + ALL its inference results
 * - Only specific results checked → export parent image + ONLY those checked results
 * - Images with no results → exported with inferenceResults: []
 */
export const buildExportManifest = (
  images: Images[],
  checkedImages: Set<number>,
  checkedResults: Set<string>,
  getResultsForImage: (
    index: number,
  ) => Array<{ modelConfigId: string; result: InferenceResult }>,
  allResults: Map<string, InferenceResult>,
): ExportManifest => {
  // Determine which images to include
  const imageIndices = new Set<number>();
  for (const idx of checkedImages) {
    imageIndices.add(idx);
  }
  // Results checked → include their parent image
  for (const key of checkedResults) {
    const imageIndex = parseInt(key.split(":")[0], 10);
    if (!isNaN(imageIndex)) {
      imageIndices.add(imageIndex);
    }
  }

  // Track used sha256 values for collision handling
  const usedFileNames = new Map<string, number>();

  const exportImages: ExportImageEntry[] = [];
  for (const img of images) {
    if (!imageIndices.has(img.index)) continue;

    // Determine filename from sha256
    const sha = img.sha256 || "unknown";
    const count = usedFileNames.get(sha) ?? 0;
    usedFileNames.set(sha, count + 1);
    const suffix = String(count).padStart(2, "0");

    // Detect extension from data URL
    const ext = img.src.startsWith("data:image/jpeg") ? "jpg" : "png";
    const fileName = `images/${sha}-${suffix}.${ext}`;

    // Determine which results to include
    let resultsToExport: ResultEntry[];
    if (checkedImages.has(img.index)) {
      // Image checked → all results
      resultsToExport = getResultsForImage(img.index);
    } else {
      // Only specific results checked
      resultsToExport = [];
      for (const key of checkedResults) {
        const imageIndex = parseInt(key.split(":")[0], 10);
        if (imageIndex !== img.index) continue;
        const result = allResults.get(key);
        if (result) {
          const modelConfigId = key.slice(key.indexOf(":") + 1);
          resultsToExport.push({ modelConfigId, result });
        }
      }
    }

    const inferenceResults: ExportInferenceEntry[] = resultsToExport.map(
      ({ modelConfigId, result }) => {
        const isEdited = modelConfigId.includes(":edited-");
        const boxes: ExportBoxEntry[] = result.boxes.map((box, i) => ({
          boxId: box.boxId,
          label: box.label,
          classId: box.classId,
          score: result.scores[i] ?? 0,
          bboxSource: box.bboxSource,
          isVerified: box.isVerified,
          coordinates: {
            topX: box.topX,
            topY: box.topY,
            bottomX: box.bottomX,
            bottomY: box.bottomY,
          },
          topNClassifications: result.topN[i] ?? [],
        }));

        return {
          modelConfigId,
          isEdited,
          completedAt: result.completedAt,
          models: result.models,
          totalBoxes: result.totalBoxes,
          labelOccurrence: result.labelOccurrence,
          boxes,
          minBoxSize: result.minBoxSize,
        };
      },
    );

    exportImages.push({
      fileName,
      fileSha256: img.sha256,
      metadata: {
        imageName: img.metadata.imageName,
        deviceBrandId: img.metadata.deviceBrandId,
        deviceModelId: img.metadata.deviceModelId,
        deviceLensId: img.metadata.deviceLensId,
        trayCode: img.metadata.trayCode,
        description: img.metadata.description,
      },
      dimensions: {
        width: img.imageDims[0] ?? 0,
        height: img.imageDims[1] ?? 0,
      },
      inferenceResults,
    });
  }

  return {
    version: "1.0",
    exportedAt: new Date().toISOString(),
    application: "nachet-mini",
    images: exportImages,
  };
}

/**
 * Escape a CSV field: wrap in double-quotes if it contains comma, quote, or newline.
 */
const escapeCsvField = (value: string): string => {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

/**
 * Generate a flat CSV string from the manifest.
 * One row per bounding box across all images and inference results.
 */
export const generateCsvFromManifest = (
  manifest: ExportManifest,
  options?: { humanReadable?: boolean; includeAnnotatedImages?: boolean },
): string => {
  const header =
    "filename,box_number,annotated_image,datetime,model,topX,topY,botX,botY,bbox_source,top1,conf1,top2,conf2,top3,conf3,top4,conf4,top5,conf5";
  const rows: string[] = [header];

  for (const img of manifest.images) {
    for (const inf of img.inferenceResults) {
      for (let boxIdx = 0; boxIdx < inf.boxes.length; boxIdx++) {
        const box = inf.boxes[boxIdx];
        const topN = box.topNClassifications;
        const csvFileName =
          options?.humanReadable && img.metadata.imageName
            ? `images/${img.metadata.imageName}`
            : img.fileName;
        const annotatedImage =
          options?.includeAnnotatedImages && inf.annotatedFileName
            ? inf.annotatedFileName
            : "";
        const fields: string[] = [
          escapeCsvField(csvFileName),
          String(boxIdx + 1),
          escapeCsvField(annotatedImage),
          escapeCsvField(inf.completedAt),
          escapeCsvField(inf.modelConfigId),
          String(box.coordinates.topX),
          String(box.coordinates.topY),
          String(box.coordinates.bottomX),
          String(box.coordinates.bottomY),
          box.bboxSource,
        ];
        for (let i = 0; i < 5; i++) {
          if (i < topN.length) {
            fields.push(escapeCsvField(topN[i].label));
            fields.push(String(topN[i].score));
          } else {
            fields.push("");
            fields.push("");
          }
        }
        rows.push(fields.join(","));
      }
    }
  }

  return rows.join("\n");
}

/**
 * Sanitize a model config ID for use in filenames.
 */
const sanitizeModelConfigId = (modelConfigId: string): string => {
  return modelConfigId.replace(/[^a-zA-Z0-9-]/g, "_");
}

/**
 * Load a base64 data URL into an HTMLImageElement.
 */
const loadImage = (src: string): Promise<HTMLImageElement> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error("Failed to load image"));
    img.src = src;
  });
}

/**
 * Draw bounding boxes and box numbers onto an image, returning a PNG blob.
 */
export const drawAnnotatedImage = async (
  imageSrc: string,
  boxes: ExportBoxEntry[],
  minBoxSize: number,
): Promise<Blob> => {
  const img = await loadImage(imageSrc);
  const canvas = document.createElement("canvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Failed to get canvas 2d context");

  ctx.drawImage(img, 0, 0);

  for (let i = 0; i < boxes.length; i++) {
    const box = boxes[i];
    const { topX, topY, bottomX, bottomY } = box.coordinates;
    const w = Math.abs(bottomX - topX);
    const h = Math.abs(bottomY - topY);
    const small = Math.max(w, h) < minBoxSize;
    const color = small ? "rgba(255,0,0,0.7)" : "rgba(128,0,128,0.7)";

    // Draw bounding box
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(topX, topY, bottomX - topX, bottomY - topY);

    // Draw box number
    const boxNumber = String(i + 1);
    ctx.font = "bold 20px sans-serif";
    const labelAtBottom = topY < 40;
    const textX = topX;
    const textY = labelAtBottom ? bottomY + 18 : topY - 6;

    // Background for readability
    const metrics = ctx.measureText(boxNumber);
    const textW = metrics.width + 6;
    const textH = 22;
    ctx.fillStyle = "rgba(255,255,255,0.8)";
    ctx.fillRect(textX - 1, textY - textH + 4, textW, textH);

    // Number text
    ctx.fillStyle = color;
    ctx.fillText(boxNumber, textX + 2, textY);
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("Failed to create annotated image blob"));
    }, "image/png");
  });
}

/**
 * Generate a ZIP file from the manifest and image data, then trigger download.
 */
export const generateExportZip = async (
  manifest: ExportManifest,
  images: Images[],
  options?: {
    includeImages?: boolean;
    includeResults?: boolean;
    includeCsv?: boolean;
    humanReadable?: boolean;
    includeAnnotatedImages?: boolean;
  },
): Promise<void> => {
  const zip = new JSZip();
  const includeImages = options?.includeImages ?? true;
  const includeResults = options?.includeResults ?? true;
  const includeCsv = options?.includeCsv ?? true;
  const humanReadable = options?.humanReadable ?? false;
  const includeAnnotatedImages = options?.includeAnnotatedImages ?? false;

  // Check for duplicate image names when human-readable is enabled
  if (humanReadable && (includeImages || includeAnnotatedImages)) {
    const nameCounts = new Map<string, number>();
    for (const entry of manifest.images) {
      const name = entry.metadata.imageName;
      nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1);
    }
    for (const [name, count] of nameCounts) {
      if (count > 1) {
        throw new Error(`DUPLICATE_NAME:${name}`);
      }
    }
  }

  // Compute annotated filenames before CSV generation so the column is populated
  if (includeAnnotatedImages) {
    for (const entry of manifest.images) {
      const imageBaseName =
        humanReadable && entry.metadata.imageName
          ? entry.metadata.imageName
          : entry.fileName.replace("images/", "").replace(/\.[^.]+$/, "");
      for (const inf of entry.inferenceResults) {
        const sanitizedId = sanitizeModelConfigId(inf.modelConfigId);
        inf.annotatedFileName = `annotated_images/${imageBaseName}_${sanitizedId}.png`;
      }
    }
  }

  // Add manifest only when results JSON is requested
  if (includeResults) {
    zip.file("manifest.json", JSON.stringify(manifest, null, 2));
  }

  // Add images
  if (includeImages) {
    const imagesFolder = zip.folder("images");
    if (!imagesFolder) throw new Error("Failed to create images folder in ZIP");

    for (const entry of manifest.images) {
      const img = images.find(
        (i) =>
          i.sha256 === entry.fileSha256 ||
          i.metadata.imageName === entry.metadata.imageName,
      );
      if (!img) continue;

      const base64Data = img.src.replace(/^data:image\/\w+;base64,/, "");
      const baseName =
        humanReadable && entry.metadata.imageName
          ? entry.metadata.imageName
          : entry.fileName.replace("images/", "");
      imagesFolder.file(baseName, base64Data, { base64: true });
    }
  }

  // Add annotated images
  if (includeAnnotatedImages) {
    const annotatedFolder = zip.folder("annotated_images");
    if (!annotatedFolder)
      throw new Error("Failed to create annotated_images folder in ZIP");

    for (const entry of manifest.images) {
      const img = images.find(
        (i) =>
          i.sha256 === entry.fileSha256 ||
          i.metadata.imageName === entry.metadata.imageName,
      );
      if (!img) continue;

      for (const inf of entry.inferenceResults) {
        if (inf.boxes.length === 0 || !inf.annotatedFileName) continue;
        const blob = await drawAnnotatedImage(
          img.src,
          inf.boxes,
          inf.minBoxSize,
        );
        const fileName = inf.annotatedFileName.replace("annotated_images/", "");
        annotatedFolder.file(fileName, blob);
      }
    }
  }

  // Add CSV
  if (includeCsv) {
    const csv = generateCsvFromManifest(manifest, {
      humanReadable,
      includeAnnotatedImages,
    });
    zip.file("results.csv", csv);
  }

  const d = new Date();
  const dateStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  const content = await zip.generateAsync({ type: "blob" });
  saveAs(content, `nachet-mini-export-${dateStr}.zip`);
}
