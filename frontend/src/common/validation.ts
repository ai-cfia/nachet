import { z } from "zod";

// Directory name validation - alphanumeric, hyphens, underscores, no spaces at start/end
export const directoryNameSchema = z
  .string()
  .transform((val) => val.trim())
  .refine((val) => val.length > 0, "Directory name cannot be empty")
  .refine((val) => val.length <= 255, "Directory name is too long")
  .refine(
    (val) => /^[a-zA-Z0-9][a-zA-Z0-9\-_]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$/.test(val),
    "Directory name must contain only letters, numbers, hyphens, and underscores, and cannot start or end with a hyphen or underscore",
  );

// Email validation
export const emailSchema = z
  .string()
  .min(1, "Email is required")
  .refine((val) => {
    const trimmed = val.trim();
    try {
      // Very strict email regex
      const emailRegex =
        /^[a-zA-Z0-9._%+-]+@([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$/;
      return emailRegex.test(trimmed) && !trimmed.includes("..");
    } catch {
      return false;
    }
  }, "Please enter a valid email address")
  .transform((val) => val.trim().toLowerCase())
  .refine((val) => val.length <= 254, "Email is too long");

// Password validation - at least 8 characters, mix of letters and numbers
export const passwordSchema = z
  .string()
  .min(8, "Password must be at least 8 characters long")
  .max(128, "Password is too long")
  .regex(
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
    "Password must contain at least one uppercase letter, one lowercase letter, and one number",
  );

// Folder name validation - similar to directory but can be empty
export const folderNameSchema = z
  .string()
  .max(255, "Folder name is too long")
  .regex(
    /^[a-zA-Z0-9\-_]*$/,
    "Folder name can only contain letters, numbers, hyphens, and underscores",
  )
  .transform((val) => val.trim());

// Seed count validation - positive integer
export const seedCountSchema = z
  .number()
  .int("Seed count must be a whole number")
  .min(1, "Seed count must be at least 1")
  .max(100, "Seed count cannot exceed 100");

// Zoom level validation - positive number
export const zoomLevelSchema = z
  .number()
  .min(0.1, "Zoom level must be at least 0.1")
  .max(100, "Zoom level cannot exceed 100");

// Image label validation - alphanumeric with spaces and basic punctuation
export const imageLabelSchema = z
  .string()
  .min(1, "Image label cannot be empty")
  .max(100, "Image label is too long")
  .regex(
    /^[a-zA-Z0-9\s\-_.,()]+$/,
    "Image label can only contain letters, numbers, spaces, hyphens, underscores, periods, commas, and parentheses",
  )
  .transform((val) => val.trim());

// Class label validation - alphanumeric with spaces
export const classLabelSchema = z
  .string()
  .min(1, "Class label cannot be empty")
  .max(100, "Class label is too long")
  .regex(
    /^[a-zA-Z0-9\s\-_]+$/,
    "Class label can only contain letters, numbers, spaces, hyphens, and underscores",
  )
  .transform((val) => val.trim());

// File validation schemas
export const imageFileSchema = z
  .instanceof(File)
  .refine(
    (file) => file.size <= 10 * 1024 * 1024,
    "File size must be less than 10MB",
  )
  .refine(
    (file) => ["image/png"].includes(file.type),
    "File must be a valid image format (PNG)",
  );

export const fileListSchema = z
  .instanceof(FileList)
  .refine((files) => files.length > 0, "At least one file must be selected")
  .refine(
    (files) => files.length <= 100,
    "Cannot upload more than 100 files at once",
  )
  .refine((files) => {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file.size > 10 * 1024 * 1024) return false;
      if (!["image/png"].includes(file.type)) return false;
    }
    return true;
  }, "All files must be valid images under 10MB each");

// Device ID validation
export const deviceIdSchema = z
  .string()
  .min(1, "Device ID cannot be empty")
  .max(100, "Device ID is too long");

// Image format validation
export const imageFormatSchema = z.enum(["image/png"]);

// Boolean validation for checkboxes
export const booleanSchema = z.boolean();

// Sanitization helpers
export const sanitizeString = (str: string): string => {
  return str.replace(/[<>/]/g, "").trim();
};

export const sanitizeEmail = (email: string): string => {
  return email.trim().toLowerCase();
};

export const sanitizeFileName = (name: string): string => {
  return name.replace(/[^a-zA-Z0-9\-_.\s()]/g, "").trim();
};

// Validation result types
export type DirectoryName = z.infer<typeof directoryNameSchema>;
export type Email = z.infer<typeof emailSchema>;
export type Password = z.infer<typeof passwordSchema>;
export type FolderName = z.infer<typeof folderNameSchema>;
export type SeedCount = z.infer<typeof seedCountSchema>;
export type ZoomLevel = z.infer<typeof zoomLevelSchema>;
export type ImageLabel = z.infer<typeof imageLabelSchema>;
export type ClassLabel = z.infer<typeof classLabelSchema>;
export type ImageFile = z.infer<typeof imageFileSchema>;
export type FileListValidated = z.infer<typeof fileListSchema>;
export type DeviceId = z.infer<typeof deviceIdSchema>;
export type ImageFormat = z.infer<typeof imageFormatSchema>;
