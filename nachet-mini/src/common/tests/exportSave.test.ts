// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { saveAs } from "file-saver";
import {
  ExportCancelledError,
  getDefaultExportFileName,
  normalizeExportFileName,
  saveExportBlob,
} from "../exportSave";

vi.mock("file-saver", () => ({ saveAs: vi.fn() }));

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("getDefaultExportFileName", () => {
  it("builds a dated zip filename", () => {
    expect(getDefaultExportFileName(new Date("2026-05-28T12:00:00Z"))).toBe(
      "nachet-mini-export-2026-05-28.zip",
    );
  });
});

describe("normalizeExportFileName", () => {
  it("keeps zip filenames unchanged", () => {
    expect(normalizeExportFileName("custom-export.zip")).toBe(
      "custom-export.zip",
    );
  });

  it("adds a zip extension when missing", () => {
    expect(normalizeExportFileName("custom-export")).toBe("custom-export.zip");
  });

  it("removes path separators and reserved filename characters", () => {
    expect(normalizeExportFileName("../bad:name?.zip")).toBe("bad-name.zip");
  });
});

describe("saveExportBlob", () => {
  const content = new Blob(["zip"]);

  it("falls back to file-saver when the browser save picker is unavailable", async () => {
    await saveExportBlob(content, "custom-export.zip");

    expect(saveAs).toHaveBeenCalledWith(content, "custom-export.zip");
  });

  it("uses the browser save picker when available", async () => {
    const write = vi.fn().mockResolvedValue(undefined);
    const close = vi.fn().mockResolvedValue(undefined);
    const createWritable = vi.fn().mockResolvedValue({ write, close });
    const showSaveFilePicker = vi.fn().mockResolvedValue({ createWritable });
    vi.stubGlobal("showSaveFilePicker", showSaveFilePicker);

    await saveExportBlob(content, "custom-export.zip");

    expect(showSaveFilePicker).toHaveBeenCalledWith(
      expect.objectContaining({ suggestedName: "custom-export.zip" }),
    );
    expect(write).toHaveBeenCalledWith(content);
    expect(close).toHaveBeenCalledOnce();
    expect(saveAs).not.toHaveBeenCalled();
  });

  it("throws ExportCancelledError when the browser save picker is cancelled", async () => {
    vi.stubGlobal(
      "showSaveFilePicker",
      vi.fn().mockRejectedValue(new DOMException("cancelled", "AbortError")),
    );

    await expect(
      saveExportBlob(content, "custom-export.zip"),
    ).rejects.toBeInstanceOf(ExportCancelledError);
  });
});
