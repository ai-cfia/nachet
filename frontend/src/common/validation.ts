import { z } from "zod";
import sanitizeHtml from "sanitize-html";

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

/**
 * Enhanced image file schema with dimension validation
 * Note: This only does basic file validation. Use validateImageFile() utility for dimension checking
 */
export const imageFileWithDimensionsSchema = imageFileSchema;

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

// XSS-Safe Validation Schemas

/**
 * Safe text input that automatically escapes HTML on output
 * Use this for any user text that will be displayed in HTML
 */
export const safeTextSchema = z
  .string()
  .min(1, "Text cannot be empty")
  .max(1000, "Text is too long")
  .transform((val) => val.trim())
  .refine((val) => val.length > 0, "Text cannot be empty");

/**
 * Safe HTML content that rejects any HTML input
 * Use sparingly - prefer plain text when possible
 */
export const safeHtmlSchema = z
  .string()
  .max(10000, "Content is too long")
  .transform((val) => val.trim())
  .refine(
    (val) => !/<[^>]*>/.test(val),
    "HTML tags are not allowed - please use plain text only",
  )
  .refine(
    (val) => !/&lt;|&gt;|&amp;|&quot;|&#x27;|&#x2F;|&#x60;|&#x3D;/.test(val),
    "HTML entities are not allowed - please use plain text only",
  );

/**
 * Safe URL validation that prevents XSS via URLs
 */
export const safeUrlSchema = z
  .string()
  .min(1, "URL cannot be empty")
  .max(2048, "URL is too long")
  .transform((val) => sanitizeUrl(val.trim()))
  .refine((val) => val !== null, "Invalid or unsafe URL");

/**
 * Safe user input for display names, comments, etc.
 * Rejects any input containing HTML tags or entities
 */
export const safeUserInputSchema = z
  .string()
  .min(1, "Input cannot be empty")
  .max(500, "Input is too long")
  .transform((val) => val.trim())
  .refine((val) => val.length > 0, "Input cannot be empty after trimming")
  .refine(
    (val) => !/<[^>]*>/.test(val),
    "HTML tags are not allowed - please use plain text only",
  )
  .refine(
    (val) => !/&lt;|&gt;|&amp;|&quot;|&#x27;|&#x2F;|&#x60;|&#x3D;/.test(val),
    "HTML entities are not allowed - please use plain text only",
  )
  .refine(
    (val) => !/<script|javascript:|data:|vbscript:/i.test(val),
    "Potentially unsafe content detected",
  );

/**
 * Enhanced image label with XSS protection - rejects HTML
 */
export const safeImageLabelSchema = z
  .string()
  .min(1, "Image label cannot be empty")
  .max(100, "Image label is too long")
  .regex(
    /^[a-zA-Z0-9\s\-_.,()]+$/,
    "Image label can only contain letters, numbers, spaces, hyphens, underscores, periods, commas, and parentheses",
  )
  .transform((val) => val.trim())
  .refine(
    (val) => !/<[^>]*>/.test(val),
    "HTML tags are not allowed in image labels",
  )
  .refine(
    (val) => !/&lt;|&gt;|&amp;|&quot;|&#x27;|&#x2F;|&#x60;|&#x3D;/.test(val),
    "HTML entities are not allowed in image labels",
  )
  .refine(
    (val) => !/javascript:|data:|vbscript:/i.test(val),
    "Unsafe protocols are not allowed in image labels",
  );

/**
 * Enhanced class label with XSS protection - rejects HTML
 */
export const safeClassLabelSchema = z
  .string()
  .min(1, "Class label cannot be empty")
  .max(100, "Class label is too long")
  .regex(
    /^[a-zA-Z0-9\s\-_]+$/,
    "Class label can only contain letters, numbers, spaces, hyphens, and underscores",
  )
  .transform((val) => val.trim())
  .refine(
    (val) => !/<[^>]*>/.test(val),
    "HTML tags are not allowed in class labels",
  )
  .refine(
    (val) => !/&lt;|&gt;|&amp;|&quot;|&#x27;|&#x2F;|&#x60;|&#x3D;/.test(val),
    "HTML entities are not allowed in class labels",
  )
  .refine(
    (val) => !/javascript:|data:|vbscript:/i.test(val),
    "Unsafe protocols are not allowed in class labels",
  );

// XSS Protection and Sanitization Helpers

/**
 * Escapes HTML special characters to prevent XSS attacks
 * Use this when rendering user input in HTML contexts
 */
export const escapeHtml = (str: string): string => {
  const htmlEscapeMap: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
    "/": "&#x2F;",
    "`": "&#x60;",
    "=": "&#x3D;",
  };

  return str.replace(/[&<>"'`=/]/g, (char) => htmlEscapeMap[char] || char);
};

/**
 * Escapes characters for safe use in HTML attributes
 * Use this when rendering user input in HTML attribute values
 */
export const escapeHtmlAttribute = (str: string): string => {
  return str
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
};

/**
 * Escapes characters for safe use in JavaScript strings
 * Use this when rendering user input in JavaScript contexts
 */
export const escapeJavaScript = (str: string): string => {
  const jsEscapeMap: Record<string, string> = {
    "\\": "\\\\",
    '"': '\\"',
    "'": "\\'",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\b": "\\b",
    "\f": "\\f",
    "\v": "\\v",
    "\0": "\\0",
    "<": "\\u003C",
    ">": "\\u003E",
    "&": "\\u0026",
    "=": "\\u003D",
  };

  return str.replace(
    /[\\"'\n\r\t\b\f\v\0<>&=]/g,
    (char) => jsEscapeMap[char] || char,
  );
};

/**
 * Validates and sanitizes URLs to prevent javascript: and data: URL attacks
 * Uses sanitize-html for initial validation with custom checks as fallback
 */
export const sanitizeUrl = (url: string): string | null => {
  const trimmed = url.trim();

  // First, use sanitize-html to validate the URL in a link context
  const testHtml = `<a href="${trimmed}">test</a>`;
  const sanitized = sanitizeHtml(testHtml, {
    allowedTags: ["a"],
    allowedAttributes: {
      a: ["href"],
    },
    allowedSchemes: ["http", "https", "ftp", "mailto"],
    allowProtocolRelative: false,
  });

  // If sanitize-html removed the href attribute, the URL is dangerous
  if (!sanitized.includes('href="')) {
    return null;
  }

  // Extract the sanitized URL
  const hrefMatch = sanitized.match(/href="([^"]*)"/);
  if (!hrefMatch) {
    return null;
  }

  const sanitizedUrl = hrefMatch[1];

  // Additional custom validation for edge cases
  const normalizedForCheck = (() => {
    // Remove control chars, whitespace, and null bytes that could be used for obfuscation
    let compact = trimmed.replace(
      // eslint-disable-next-line no-control-regex
      /[\u0000-\u001F\s\u007F-\u009F\u00A0\uFEFF]+/g,
      "",
    );

    // Multiple decode passes to handle nested encoding
    for (let i = 0; i < 3; i++) {
      try {
        const decoded = decodeURIComponent(compact);
        if (decoded === compact) break; // No more changes
        compact = decoded;
      } catch {
        break;
      }
    }

    return compact.toLowerCase();
  })();

  // Additional checks for obfuscated scripts
  if (
    normalizedForCheck.includes("script") ||
    normalizedForCheck.includes("eval") ||
    normalizedForCheck.includes("expression")
  ) {
    return null;
  }

  return sanitizedUrl;
};

/**
 * Checks if a string contains HTML tags or entities
 * Returns true if HTML is detected, false otherwise
 */
export const containsHtml = (str: string): boolean => {
  // Check for HTML tags
  if (/<[^>]*>/.test(str)) return true;

  // Check for common HTML entities
  const htmlEntities = /&lt;|&gt;|&amp;|&quot;|&#x27;|&#x2F;|&#x60;|&#x3D;/;
  if (htmlEntities.test(str)) return true;

  return false;
};

/**
 * Removes potentially dangerous HTML tags and attributes using sanitize-html
 * @deprecated Use containsHtml() to reject HTML input instead of sanitizing
 * Use sparingly - prefer escaping over stripping when possible
 */
export const stripDangerousHtml = (str: string): string => {
  // First sanitize HTML using sanitize-html
  let result = sanitizeHtml(str, {
    allowedTags: [
      // Basic formatting tags - safe to preserve
      "p",
      "br",
      "strong",
      "b",
      "em",
      "i",
      "u",
      "span",
      "div",
      "h1",
      "h2",
      "h3",
      "h4",
      "h5",
      "h6",
      "ul",
      "ol",
      "li",
      "blockquote",
      "a",
      "img",
    ],
    allowedAttributes: {
      a: ["href"], // Only href for links
      img: ["src", "alt"], // Only src and alt for images
    },
    allowedSchemes: ["http", "https", "mailto"], // Only safe URL schemes
    disallowedTagsMode: "discard", // Remove disallowed tags entirely
    allowProtocolRelative: false, // Block protocol-relative URLs
    enforceHtmlBoundary: false, // Don't require html tags
    parseStyleAttributes: false, // Don't parse style attributes for security
  });

  // Also handle plain text dangerous URLs that sanitize-html might miss
  result = result
    .replace(/javascript\s*:/gi, "") // Remove javascript: URLs
    .replace(/data\s*:/gi, "") // Remove data: URLs
    .replace(/vbscript\s*:/gi, "") // Remove vbscript: URLs
    .trim();

  return result;
};

/**
 * Sanitizes HTML content using sanitize-html library with safe defaults
 * Allows basic formatting tags but removes all dangerous content
 * Use this when you need to preserve some HTML formatting
 */
export const sanitizeHtmlContent = (html: string): string => {
  return sanitizeHtml(html, {
    allowedTags: ["b", "i", "em", "strong", "p", "br"], // Only basic formatting
    allowedAttributes: {}, // No attributes allowed
    allowedSchemes: ["http", "https", "mailto"], // Only safe URL schemes
    disallowedTagsMode: "discard", // Remove disallowed tags entirely
    allowProtocolRelative: false, // Block protocol-relative URLs
    enforceHtmlBoundary: false, // Don't require html tags
    parseStyleAttributes: false, // Don't parse style attributes for security
  }).trim();
};

/**
 * Content Security Policy helpers
 */
export const cspDirectives = {
  defaultSrc: "'self'",
  scriptSrc: "'self' 'unsafe-inline'", // Consider removing unsafe-inline in production
  styleSrc: "'self' 'unsafe-inline'",
  imgSrc: "'self' data: blob:",
  connectSrc: "'self'",
  fontSrc: "'self'",
  objectSrc: "'none'",
  mediaSrc: "'self'",
  frameSrc: "'none'",
  baseUri: "'self'",
  formAction: "'self'",
  frameAncestors: "'none'",
  upgradeInsecureRequests: true,
} as const;

/**
 * Generates a Content Security Policy header value
 */
export const generateCSP = (): string => {
  const directives = Object.entries(cspDirectives)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => {
      const kebabKey = key.replace(/([A-Z])/g, "-$1").toLowerCase();
      if (typeof value === "boolean") {
        return value ? kebabKey : "";
      }
      return `${kebabKey} ${value}`;
    })
    .filter((directive) => directive.length > 0);

  return directives.join("; ");
};

// Legacy sanitization helpers (maintained for backward compatibility)
/**
 * Trims whitespace and provides basic text cleaning with XSS protection.
 * Now strictly returns an escaped version of the string (no partial unescaping) to avoid incomplete multi-character sanitization issues.
 * For advanced XSS protection, consider using `safeTextSchema` for input validation.
 */
export const sanitizeString = (str: string): string => {
  return escapeHtml(str).trim();
};

/**
 * Normalizes email addresses by trimming and converting to lowercase.
 * This is not deprecated as it performs standard email normalization.
 */
export const sanitizeEmail = (email: string): string => {
  return email.trim().toLowerCase();
};

/**
 * Removes potentially dangerous characters from filenames.
 * This is not deprecated as it serves a specific purpose for file handling.
 */
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

// XSS-Safe validation result types
export type SafeText = z.infer<typeof safeTextSchema>;
export type SafeHtml = z.infer<typeof safeHtmlSchema>;
export type SafeUrl = z.infer<typeof safeUrlSchema>;
export type SafeUserInput = z.infer<typeof safeUserInputSchema>;
export type SafeImageLabel = z.infer<typeof safeImageLabelSchema>;
export type SafeClassLabel = z.infer<typeof safeClassLabelSchema>;

// Utility types for XSS protection
export type EscapedString = string & { readonly __escaped: unique symbol };
export type SanitizedUrl = string & { readonly __sanitized: unique symbol };

// ==========================================
// API Response Validation Schemas
// ==========================================

// Base coordinate schema for API responses
export const BoxCoordinatesSchema = z.object({
  topX: z.number(),
  topY: z.number(),
  bottomX: z.number(),
  bottomY: z.number(),
});

// Inference box schema from API response
export const InferenceBoxApiSchema = z.object({
  topN: z.array(
    z.object({
      score: z.number(),
      label: z.string(),
    }),
  ),
  score: z.number(),
  label: z.string(),
  classId: z.string(),
  object_type_id: z.string(),
  box_id: z.string(),
  box: BoxCoordinatesSchema,
  overlapping: z.boolean(),
  overlappingIndices: z.number(),
  is_verified: z.boolean().optional(),
});

// API Inference Data schema
export const ApiInferenceDataSchema = z.object({
  filename: z.string(),
  imageId: z.string(),
  inference_id: z.string(),
  boxes: z.array(InferenceBoxApiSchema),
  labelOccurrence: z.record(z.string(), z.number()),
  totalBoxes: z.number(),
  models: z.array(
    z.object({
      name: z.string(),
      version: z.number(),
    }),
  ),
});

// Model Metadata schema
export const ModelMetadataSchema = z.object({
  created_by: z.string(),
  creation_date: z.string(),
  dataset: z.string(),
  description: z.string(),
  identifiable: z.array(z.string()),
  job_name: z.string(),
  metrics: z.array(z.string()),
  model_name: z.string(),
  models: z.array(z.string()),
  pipeline_name: z.string(),
  default: z.boolean().optional(),
});

// Species Data schema
export const ApiSpeciesDataSchema = z.object({
  seeds: z.array(
    z.object({
      seed_id: z.string(),
      name_code: z.string(),
      family: z.string(),
      genus: z.string(),
      species: z.string(),
      seed_name: z.string().nullable().optional(),
      id: z.number().optional(),
      label: z.string().optional(),
    }),
  ),
});

// Azure Storage Directory schemas
export const DirectoryPictureApiSchema = z.object({
  inference_exists: z.boolean(),
  is_validation: z.boolean(),
  picture_id: z.string(),
});

export const AzureStorageDirectoryItemApiSchema = z.object({
  id: z.string(),
  name: z.string(),
  folder_prefix: z.string(),
  description: z.string().nullable(),
  picture_count: z.number(),
  // pictures: z.array(DirectoryPictureApiSchema),
});

export const ReadAzureStorageDirApiSchema = z.object({
  directories: z.array(AzureStorageDirectoryItemApiSchema),
});

// Simple response schemas
export const UserIdResponseSchema = z.object({
  user_id: z.string(),
});

export const SessionIdResponseSchema = z.object({
  session_id: z.string(),
});

export const BooleanResponseSchema = z.boolean();

export const IsRegisteredResponseSchema = z.object({
  is_registered: z.boolean(),
});

// Void response for operations that don't return data (but still succeed)
export const VoidResponseSchema = z
  .any()
  .refine(() => true, "Operation completed successfully");

// Device schemas
export const DeviceModelSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
});

export const DeviceLensSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
});

export const DeviceBrandSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  models: z.array(DeviceModelSchema),
  lenses: z.array(DeviceLensSchema),
});

export const ApiDevicesResponseSchema = z.object({
  devices: z.array(DeviceBrandSchema),
});

// Generic validation function for API responses
export function validateApiResponse<T>(
  schema: z.ZodSchema<T>,
  data: unknown,
  apiName: string,
): T {
  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error(
        `API Response validation failed for ${apiName}:`,
        error.issues,
      );
      throw new Error(
        `Invalid API response from ${apiName}: ${error.issues.map((e) => e.message).join(", ")}`,
      );
    }
    throw error;
  }
}

// API Response validation result types
export type ApiInferenceData = z.infer<typeof ApiInferenceDataSchema>;
export type ModelMetadata = z.infer<typeof ModelMetadataSchema>;
export type ApiSpeciesData = z.infer<typeof ApiSpeciesDataSchema>;
export type ReadAzureStorageDirApi = z.infer<
  typeof ReadAzureStorageDirApiSchema
>;
export type UserIdResponse = z.infer<typeof UserIdResponseSchema>;
export type SessionIdResponse = z.infer<typeof SessionIdResponseSchema>;
export type IsRegisteredResponse = z.infer<typeof IsRegisteredResponseSchema>;
export type ApiDevicesResponse = z.infer<typeof ApiDevicesResponseSchema>;
export type DeviceBrand = z.infer<typeof DeviceBrandSchema>;
export type DeviceModel = z.infer<typeof DeviceModelSchema>;
export type DeviceLens = z.infer<typeof DeviceLensSchema>;
