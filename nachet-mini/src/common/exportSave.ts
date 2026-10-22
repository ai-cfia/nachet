import { saveAs } from "file-saver";

export class ExportCancelledError extends Error {
  constructor() {
    super("Export cancelled");
    this.name = "ExportCancelledError";
  }
}

type SaveFilePickerOptions = {
  suggestedName?: string;
  types?: Array<{
    description: string;
    accept: Record<string, string[]>;
  }>;
};

type FileSystemWritableFileStream = {
  write: (data: Blob) => Promise<void>;
  close: () => Promise<void>;
};

export type FileSystemFileHandle = {
  createWritable: () => Promise<FileSystemWritableFileStream>;
};

type WindowWithSaveFilePicker = Window & {
  showSaveFilePicker?: (
    options?: SaveFilePickerOptions,
  ) => Promise<FileSystemFileHandle>;
};

export const getDefaultExportFileName = (date = new Date()): string => {
  const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  return `nachet-mini-export-${dateStr}.zip`;
};

const replaceControlCharacters = (value: string): string =>
  Array.from(value)
    .map((char) => (char.charCodeAt(0) < 32 ? "-" : char))
    .join("");

export const normalizeExportFileName = (fileName: string): string => {
  const trimmed = fileName.trim();
  const hasZipExtension = trimmed.toLowerCase().endsWith(".zip");
  const nameWithoutExtension = hasZipExtension ? trimmed.slice(0, -4) : trimmed;
  const normalized = replaceControlCharacters(nameWithoutExtension.trim())
    .replace(/[<>:"/\\|?*]/g, "-")
    .replace(/-{2,}/g, "-")
    .replace(/^[.\s-]+|[.\s-]+$/g, "");

  const safeName = normalized || getDefaultExportFileName();
  return safeName.toLowerCase().endsWith(".zip") ? safeName : `${safeName}.zip`;
};

/**
 * Open the browser Save As dialog. Must be called directly from the click
 * handler, before any slow work, or Chrome blocks it (user-activation window).
 * Returns null when the browser has no save picker (fallback to file-saver).
 */
export const requestExportFileHandle = async (
  fileName: string,
): Promise<FileSystemFileHandle | null> => {
  const picker = (window as WindowWithSaveFilePicker).showSaveFilePicker;
  if (!picker) return null;
  try {
    return await picker({
      suggestedName: fileName,
      types: [
        {
          description: "ZIP archive",
          accept: { "application/zip": [".zip"] },
        },
      ],
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ExportCancelledError();
    }
    throw error;
  }
};

export const writeExportBlob = async (
  content: Blob,
  fileName: string,
  handle: FileSystemFileHandle | null,
) => {
  if (!handle) {
    saveAs(content, fileName);
    return;
  }
  const writable = await handle.createWritable();
  await writable.write(content);
  await writable.close();
};

export const saveExportBlob = async (content: Blob, fileName: string) =>
  writeExportBlob(content, fileName, await requestExportFileHandle(fileName));
