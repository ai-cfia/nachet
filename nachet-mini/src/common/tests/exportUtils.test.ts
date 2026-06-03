// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  buildExportManifest,
  generateCsvFromManifest,
  drawAnnotatedImage,
  generateExportZip,
} from "../exportUtils";
import type { Images, InferenceResult, InferenceBox } from "../types";
import type { ExportManifest, ExportBoxEntry } from "../exportTypes";

// ---------------------------------------------------------------------------
// Hoisted mock state — must be available before vi.mock factories run
// ---------------------------------------------------------------------------
const zipMock = vi.hoisted(() => {
  const file = vi.fn();
  const imagesFolder = { file: vi.fn() };
  const annotatedFolder = { file: vi.fn() };
  const folder = vi.fn((name: string) => {
    if (name === "images") return imagesFolder;
    if (name === "annotated_images") return annotatedFolder;
    return null;
  });
  const generateAsync = vi.fn();
  const instance = { file, folder, generateAsync };
  return {
    file,
    imagesFolder,
    annotatedFolder,
    folder,
    generateAsync,
    instance,
  };
});

const exportSaveMock = vi.hoisted(() => ({
  getDefaultExportFileName: vi.fn(),
  normalizeExportFileName: vi.fn(),
  saveExportBlob: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------
vi.mock("jszip", () => {
  // Arrow functions cannot be used as constructors — use a regular function.
  function MockJSZip(this: unknown) {
    return zipMock.instance;
  }
  return { default: MockJSZip };
});

vi.mock("@common/exportSave", () => exportSaveMock);

// ---------------------------------------------------------------------------
// MockImage — triggers onload or onerror asynchronously
// ---------------------------------------------------------------------------
let mockNaturalWidth = 100;
let mockNaturalHeight = 80;
let mockImageShouldFail = false;

class MockImage {
  naturalWidth = mockNaturalWidth;
  naturalHeight = mockNaturalHeight;
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;

  set src(_: string) {
    this.naturalWidth = mockNaturalWidth;
    this.naturalHeight = mockNaturalHeight;
    Promise.resolve().then(() => {
      if (mockImageShouldFail) this.onerror?.();
      else this.onload?.();
    });
  }
}

// ---------------------------------------------------------------------------
// Canvas mock
// ---------------------------------------------------------------------------
const mockCtx = {
  drawImage: vi.fn(),
  strokeRect: vi.fn(),
  fillRect: vi.fn(),
  fillText: vi.fn(),
  measureText: vi.fn(() => ({ width: 30 })),
  strokeStyle: "" as string,
  lineWidth: 0,
  font: "",
  fillStyle: "" as string,
};

const mockCanvas = {
  width: 0,
  height: 0,
  getContext: vi.fn(() => mockCtx),
  toBlob: vi.fn((cb: (b: Blob | null) => void) =>
    cb(new Blob(["png"], { type: "image/png" })),
  ),
};

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------
const makeInferenceBox = (
  overrides: Partial<InferenceBox> = {},
): InferenceBox => ({
  inferenceId: "inf-1",
  boxId: "box-1",
  classId: "cls-1",
  label: "weed",
  isVerified: false,
  bboxSource: "model",
  topX: 10,
  topY: 20,
  bottomX: 110,
  bottomY: 120,
  ...overrides,
});

const makeInferenceResult = (
  overrides: Partial<InferenceResult> = {},
): InferenceResult => ({
  scores: [0.9],
  classifications: ["weed"],
  boxes: [makeInferenceBox()],
  topN: [[{ score: 0.9, label: "weed" }]],
  overlapping: [false],
  overlappingIndices: [],
  labelOccurrence: { weed: 1 },
  totalBoxes: 1,
  models: [{ name: "detector", version: "1.0" }],
  completedAt: "2026-01-01T00:00:00.000Z",
  isActive: false,
  minBoxSize: 50,
  ...overrides,
});

const makeImage = (overrides: Partial<Images> = {}): Images => ({
  index: 0,
  src: "data:image/png;base64,abc123",
  imageDims: [640, 480],
  sha256: "deadbeef",
  metadata: {
    imageName: "test-image",
    deviceBrandId: "tagarno",
    deviceModelId: "prestige",
    deviceLensId: "4x",
    trayCode: "A",
    description: "A test image",
  },
  ...overrides,
});

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------
beforeEach(() => {
  mockNaturalWidth = 100;
  mockNaturalHeight = 80;
  mockImageShouldFail = false;
  vi.stubGlobal("Image", MockImage);
  vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
    if (tag === "canvas") return mockCanvas as unknown as HTMLCanvasElement;
    // Fall through to real implementation for other elements
    return document.createElement.call(document, tag as "div");
  });
  exportSaveMock.getDefaultExportFileName.mockReturnValue(
    "nachet-mini-export-test.zip",
  );
  exportSaveMock.normalizeExportFileName.mockImplementation(
    (fileName: string) => `normalized-${fileName}`,
  );
  exportSaveMock.saveExportBlob.mockResolvedValue(undefined);
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// buildExportManifest
// ---------------------------------------------------------------------------
describe("buildExportManifest", () => {
  const result1 = makeInferenceResult();
  const img0 = makeImage({ index: 0, sha256: "sha0" });
  const img1 = makeImage({
    index: 1,
    sha256: "sha1",
    src: "data:image/jpeg;base64,xyz",
    metadata: { ...makeImage().metadata, imageName: "second-image" },
  });

  const getResultsForImage = (idx: number) => {
    if (idx === 0) return [{ modelConfigId: "model-a", result: result1 }];
    if (idx === 1) return [{ modelConfigId: "model-b", result: result1 }];
    return [];
  };

  it("includes an image that is in checkedImages", () => {
    const manifest = buildExportManifest(
      [img0],
      new Set([0]),
      new Set(),
      getResultsForImage,
      new Map(),
    );
    expect(manifest.images).toHaveLength(1);
    expect(manifest.images[0].fileSha256).toBe("sha0");
  });

  it("exports all results when an image is in checkedImages", () => {
    const manifest = buildExportManifest(
      [img0],
      new Set([0]),
      new Set(),
      getResultsForImage,
      new Map(),
    );
    expect(manifest.images[0].inferenceResults).toHaveLength(1);
    expect(manifest.images[0].inferenceResults[0].modelConfigId).toBe(
      "model-a",
    );
  });

  it("includes the parent image when only a result key is checked", () => {
    const allResults = new Map([["0:model-a", result1]]);
    const manifest = buildExportManifest(
      [img0],
      new Set(),
      new Set(["0:model-a"]),
      getResultsForImage,
      allResults,
    );
    expect(manifest.images).toHaveLength(1);
    expect(manifest.images[0].inferenceResults).toHaveLength(1);
    expect(manifest.images[0].inferenceResults[0].modelConfigId).toBe(
      "model-a",
    );
  });

  it("excludes an image not in either set", () => {
    const manifest = buildExportManifest(
      [img0, img1],
      new Set([1]),
      new Set(),
      getResultsForImage,
      new Map(),
    );
    expect(manifest.images.every((i) => i.fileSha256 !== "sha0")).toBe(true);
  });

  it("uses .jpg extension for JPEG source images", () => {
    const manifest = buildExportManifest(
      [img1],
      new Set([1]),
      new Set(),
      getResultsForImage,
      new Map(),
    );
    expect(manifest.images[0].fileName).toMatch(/\.jpg$/);
  });

  it("uses .png extension for non-JPEG source images", () => {
    const manifest = buildExportManifest(
      [img0],
      new Set([0]),
      new Set(),
      getResultsForImage,
      new Map(),
    );
    expect(manifest.images[0].fileName).toMatch(/\.png$/);
  });

  it("handles SHA collisions by incrementing the suffix", () => {
    const dup1 = makeImage({ index: 0, sha256: "same" });
    const dup2 = makeImage({ index: 1, sha256: "same" });
    const manifest = buildExportManifest(
      [dup1, dup2],
      new Set([0, 1]),
      new Set(),
      () => [],
      new Map(),
    );
    const names = manifest.images.map((i) => i.fileName);
    expect(names[0]).toContain("-00.");
    expect(names[1]).toContain("-01.");
  });

  it("marks isEdited=true when modelConfigId contains ':edited-'", () => {
    const editedResult = makeInferenceResult();
    const getEdited = () => [
      { modelConfigId: "model-a:edited-abc", result: editedResult },
    ];
    const manifest = buildExportManifest(
      [img0],
      new Set([0]),
      new Set(),
      getEdited,
      new Map(),
    );
    expect(manifest.images[0].inferenceResults[0].isEdited).toBe(true);
  });

  it("sets manifest metadata correctly", () => {
    const manifest = buildExportManifest(
      [img0],
      new Set([0]),
      new Set(),
      () => [],
      new Map(),
    );
    expect(manifest.version).toBe("1.0");
    expect(manifest.application).toBe("nachet-mini");
    expect(manifest.exportedAt).toBeTruthy();
  });
  it('uses "unknown" prefix when sha256 is missing', () => {
    const noShaImg = makeImage({ index: 0, sha256: "" });
    const manifest = buildExportManifest(
      [noShaImg],
      new Set([0]),
      new Set(),
      () => [],
      new Map(),
    );
    expect(manifest.images[0].fileName).toMatch(/^images\/unknown-00\./);
  });

  it("handles missing scores or topN gracefully", () => {
    const incompleteResult = makeInferenceResult({
      scores: [],
      topN: [],
    });
    const getIncomplete = () => [
      { modelConfigId: "model-a", result: incompleteResult },
    ];
    const manifest = buildExportManifest(
      [img0],
      new Set([0]),
      new Set(),
      getIncomplete,
      new Map(),
    );
    const box = manifest.images[0].inferenceResults[0].boxes[0];
    expect(box.score).toBe(0);
    expect(box.topNClassifications).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// generateCsvFromManifest
// ---------------------------------------------------------------------------
const makeExportBox = (
  overrides: Partial<ExportBoxEntry> = {},
): ExportBoxEntry => ({
  boxId: "b1",
  label: "weed",
  classId: "cls-1",
  score: 0.9,
  bboxSource: "model",
  isVerified: false,
  coordinates: { topX: 10, topY: 20, bottomX: 110, bottomY: 120 },
  topNClassifications: [
    { score: 0.9, label: "weed" },
    { score: 0.05, label: "grass" },
  ],
  ...overrides,
});

const makeManifest = (
  overrides: Partial<ExportManifest> = {},
): ExportManifest => ({
  version: "1.0",
  exportedAt: "2026-01-01T00:00:00.000Z",
  application: "nachet-mini",
  images: [
    {
      fileName: "images/sha0-00.png",
      fileSha256: "sha0",
      metadata: {
        imageName: "my-image",
        deviceBrandId: "tagarno",
        deviceModelId: "prestige",
        deviceLensId: "4x",
        trayCode: "A",
        description: "test",
      },
      dimensions: { width: 640, height: 480 },
      inferenceResults: [
        {
          modelConfigId: "model-a",
          isEdited: false,
          completedAt: "2026-01-01T00:00:00.000Z",
          models: [{ name: "detector", version: "1.0" }],
          totalBoxes: 1,
          labelOccurrence: { weed: 1 },
          boxes: [makeExportBox()],
          minBoxSize: 50,
        },
      ],
    },
  ],
  ...overrides,
});

describe("generateCsvFromManifest", () => {
  it("starts with the correct header row", () => {
    const csv = generateCsvFromManifest(makeManifest());
    const header = csv.split("\n")[0];
    expect(header).toBe(
      "filename,box_number,annotated_image,datetime,model,topX,topY,botX,botY,bbox_source,top1,conf1,top2,conf2,top3,conf3,top4,conf4,top5,conf5",
    );
  });

  it("generates one data row per box", () => {
    const manifest = makeManifest();
    manifest.images[0].inferenceResults[0].boxes = [
      makeExportBox({ boxId: "b1" }),
      makeExportBox({ boxId: "b2" }),
      makeExportBox({ boxId: "b3" }),
    ];
    const csv = generateCsvFromManifest(manifest);
    const rows = csv.split("\n");
    expect(rows).toHaveLength(4); // header + 3 boxes
  });

  it("escapes fields containing commas", () => {
    const manifest = makeManifest();
    manifest.images[0].inferenceResults[0].modelConfigId = "model,v2";
    const csv = generateCsvFromManifest(manifest);
    expect(csv).toContain('"model,v2"');
  });

  it("escapes fields containing double-quotes", () => {
    const manifest = makeManifest();
    manifest.images[0].inferenceResults[0].modelConfigId = 'model"v2';
    const csv = generateCsvFromManifest(manifest);
    expect(csv).toContain('"model""v2"');
  });

  it("uses imageName as filename when humanReadable=true", () => {
    const csv = generateCsvFromManifest(makeManifest(), {
      humanReadable: true,
    });
    expect(csv).toContain("images/my-image");
  });

  it("uses sha-based filename when humanReadable is not set", () => {
    const csv = generateCsvFromManifest(makeManifest());
    expect(csv).toContain("images/sha0-00.png");
  });

  it("populates annotated_image column when includeAnnotatedImages=true and annotatedFileName is set", () => {
    const manifest = makeManifest();
    manifest.images[0].inferenceResults[0].annotatedFileName =
      "annotated_images/sha0-00_model-a.png";
    const csv = generateCsvFromManifest(manifest, {
      includeAnnotatedImages: true,
    });
    expect(csv).toContain("annotated_images/sha0-00_model-a.png");
  });

  it("pads missing topN classifications with empty strings", () => {
    const manifest = makeManifest();
    // box with only 1 topN entry instead of 5
    manifest.images[0].inferenceResults[0].boxes[0].topNClassifications = [
      { score: 0.9, label: "weed" },
    ];
    const csv = generateCsvFromManifest(manifest);
    const dataRow = csv.split("\n")[1];
    const fields = dataRow.split(",");
    // top1=weed, conf1=0.9, then 8 empty fields (4 pairs)
    expect(fields[fields.length - 1]).toBe("");
    expect(fields[fields.length - 2]).toBe("");
  });

  it("escapes fields containing newlines", () => {
    const manifest = makeManifest();
    manifest.images[0].inferenceResults[0].modelConfigId =
      "model\nwith\nnewlines";
    const csv = generateCsvFromManifest(manifest);
    expect(csv).toContain('"model\nwith\nnewlines"');
  });

  it("falls back to sha-based filename if humanReadable=true but imageName is empty", () => {
    const manifest = makeManifest();
    manifest.images[0].metadata.imageName = ""; // Empty image name
    const csv = generateCsvFromManifest(manifest, { humanReadable: true });
    expect(csv).toContain("images/sha0-00.png");
  });
});

// ---------------------------------------------------------------------------
// drawAnnotatedImage
// ---------------------------------------------------------------------------
describe("drawAnnotatedImage", () => {
  const normalBox: ExportBoxEntry = {
    boxId: "b1",
    label: "weed",
    classId: "cls-1",
    score: 0.9,
    bboxSource: "model",
    isVerified: false,
    coordinates: { topX: 10, topY: 50, bottomX: 110, bottomY: 150 }, // 100×100, topY>=40
    topNClassifications: [],
  };

  const smallBox: ExportBoxEntry = {
    ...normalBox,
    boxId: "b2",
    coordinates: { topX: 10, topY: 50, bottomX: 20, bottomY: 60 }, // 10×10 → small
  };

  const topLabelBox: ExportBoxEntry = {
    ...normalBox,
    boxId: "b3",
    coordinates: { topX: 10, topY: 10, bottomX: 110, bottomY: 110 }, // topY < 40
  };

  beforeEach(() => {
    mockCanvas.getContext.mockReturnValue(mockCtx);
    mockCanvas.toBlob.mockImplementation((cb: (b: Blob | null) => void) =>
      cb(new Blob(["png"], { type: "image/png" })),
    );
  });

  it("returns a Blob", async () => {
    const blob = await drawAnnotatedImage(
      "data:image/png;base64,abc",
      [normalBox],
      50,
    );
    expect(blob).toBeInstanceOf(Blob);
  });

  it("uses red stroke for boxes smaller than minBoxSize", async () => {
    await drawAnnotatedImage("data:image/png;base64,abc", [smallBox], 50);
    expect(mockCtx.strokeStyle).toMatch(/rgba\(255,0,0/);
  });

  it("uses purple stroke for boxes at or above minBoxSize", async () => {
    await drawAnnotatedImage("data:image/png;base64,abc", [normalBox], 50);
    expect(mockCtx.strokeStyle).toMatch(/rgba\(128,0,128/);
  });

  it("positions label below box when topY < 40", async () => {
    await drawAnnotatedImage("data:image/png;base64,abc", [topLabelBox], 50);
    // fillText should be called — we verify it was called (position logic executed)
    expect(mockCtx.fillText).toHaveBeenCalled();
  });

  it("throws when canvas 2D context is unavailable", async () => {
    mockCanvas.getContext.mockReturnValueOnce(null);
    await expect(
      drawAnnotatedImage("data:image/png;base64,abc", [normalBox], 50),
    ).rejects.toThrow("Failed to get canvas 2d context");
  });

  it("throws an error if the image fails to load", async () => {
    mockImageShouldFail = true;
    await expect(
      drawAnnotatedImage("data:image/png;base64,bad", [normalBox], 50),
    ).rejects.toThrow("Failed to load image");
  });

  it("throws an error if canvas toBlob fails to return a blob", async () => {
    mockCanvas.toBlob.mockImplementationOnce((cb: (b: Blob | null) => void) =>
      cb(null),
    );
    await expect(
      drawAnnotatedImage("data:image/png;base64,abc", [normalBox], 50),
    ).rejects.toThrow("Failed to create annotated image blob");
  });
});

// ---------------------------------------------------------------------------
// generateExportZip
// ---------------------------------------------------------------------------
describe("generateExportZip", () => {
  const images = [
    makeImage({ index: 0, sha256: "sha0", src: "data:image/png;base64,abc" }),
  ];

  beforeEach(() => {
    zipMock.generateAsync.mockResolvedValue(new Blob(["zip"]));
    zipMock.folder.mockImplementation((name: string) => {
      if (name === "images") return zipMock.imagesFolder;
      if (name === "annotated_images") return zipMock.annotatedFolder;
      return null;
    });
  });

  it("saves with the default export filename", async () => {
    await generateExportZip(makeManifest(), images);
    expect(exportSaveMock.getDefaultExportFileName).toHaveBeenCalledOnce();
    expect(exportSaveMock.normalizeExportFileName).toHaveBeenCalledWith(
      "nachet-mini-export-test.zip",
    );
    expect(exportSaveMock.saveExportBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      "normalized-nachet-mini-export-test.zip",
    );
  });

  it("saves with a custom filename", async () => {
    await generateExportZip(makeManifest(), images, {
      fileName: "custom-export.zip",
    });
    expect(exportSaveMock.getDefaultExportFileName).not.toHaveBeenCalled();
    expect(exportSaveMock.normalizeExportFileName).toHaveBeenCalledWith(
      "custom-export.zip",
    );
    expect(exportSaveMock.saveExportBlob).toHaveBeenCalledWith(
      expect.any(Blob),
      "normalized-custom-export.zip",
    );
  });

  it("does not add manifest.json when includeResults=false", async () => {
    await generateExportZip(makeManifest(), images, { includeResults: false });
    const hasManifest = zipMock.file.mock.calls.some(
      ([name]) => name === "manifest.json",
    );
    expect(hasManifest).toBe(false);
  });

  it("adds manifest.json when includeResults=true (default)", async () => {
    await generateExportZip(makeManifest(), images, {
      includeResults: true,
      includeImages: false,
    });
    const hasManifest = zipMock.file.mock.calls.some(
      ([name]) => name === "manifest.json",
    );
    expect(hasManifest).toBe(true);
  });

  it("does not add results.csv when includeCsv=false", async () => {
    await generateExportZip(makeManifest(), images, { includeCsv: false });
    const hasCsv = zipMock.file.mock.calls.some(
      ([name]) => name === "results.csv",
    );
    expect(hasCsv).toBe(false);
  });

  it("adds results.csv when includeCsv=true (default)", async () => {
    await generateExportZip(makeManifest(), images, {
      includeCsv: true,
      includeImages: false,
    });
    const hasCsv = zipMock.file.mock.calls.some(
      ([name]) => name === "results.csv",
    );
    expect(hasCsv).toBe(true);
  });

  it("throws DUPLICATE_NAME error when humanReadable=true and two images share a name", async () => {
    const base = makeManifest();
    const dupManifest: ExportManifest = {
      ...base,
      images: [
        {
          ...base.images[0],
          metadata: { ...base.images[0].metadata, imageName: "same" },
        },
        {
          ...base.images[0],
          metadata: { ...base.images[0].metadata, imageName: "same" },
        },
      ],
    };
    await expect(
      generateExportZip(dupManifest, images, {
        humanReadable: true,
        includeImages: true,
      }),
    ).rejects.toThrow("DUPLICATE_NAME:same");
  });

  it("succeeds when humanReadable=true and all image names are unique", async () => {
    const base = makeManifest();
    const uniqueManifest: ExportManifest = {
      ...base,
      images: [
        {
          ...base.images[0],
          metadata: { ...base.images[0].metadata, imageName: "unique-1" },
        },
      ],
    };
    await expect(
      generateExportZip(uniqueManifest, images, {
        humanReadable: true,
        includeImages: true,
      }),
    ).resolves.toBeUndefined();
  });

  it("populates annotatedFileName on inference entries before CSV generation", async () => {
    const mfCopy: ExportManifest = JSON.parse(JSON.stringify(makeManifest()));
    await generateExportZip(mfCopy, images, {
      includeAnnotatedImages: true,
      includeImages: false,
      includeCsv: true,
    });
    expect(mfCopy.images[0].inferenceResults[0].annotatedFileName).toMatch(
      /^annotated_images\//,
    );
  });

  it("safely skips generating files for images that are in the manifest but missing from source array", async () => {
    // Pass empty images array [] despite the manifest having an image entry
    await generateExportZip(makeManifest(), [], { includeImages: true });
    // It should not attempt to write the image file
    expect(zipMock.imagesFolder.file).not.toHaveBeenCalled();
  });
});
