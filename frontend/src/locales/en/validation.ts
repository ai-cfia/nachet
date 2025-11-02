// Validation error message translations (English)
const validation = {
  // Directory name errors
  directoryName: {
    empty: "Directory name cannot be empty",
    tooLong: "Directory name is too long",
    invalidFormat:
      "Directory name must contain only letters, numbers, hyphens, and underscores, and cannot start or end with a hyphen or underscore",
  },

  // Email errors
  email: {
    required: "Email is required",
    invalid: "Please enter a valid email address",
    tooLong: "Email is too long",
  },

  // Password errors
  password: {
    tooShort: "Password must be at least 8 characters long",
    tooLong: "Password is too long",
    weakPassword:
      "Password must contain at least one uppercase letter, one lowercase letter, and one number",
  },

  // Folder name errors
  folderName: {
    tooLong: "Folder name is too long",
    invalidFormat:
      "Folder name can only contain letters, numbers, hyphens, and underscores",
  },

  // Seed count errors
  seedCount: {
    notInteger: "Seed count must be a whole number",
    tooSmall: "Seed count must be at least 1",
    tooLarge: "Seed count cannot exceed 100",
  },

  // Zoom level errors
  zoomLevel: {
    tooSmall: "Zoom level must be at least 0.1",
    tooLarge: "Zoom level cannot exceed 100",
  },

  // Magnification errors
  magnification: {
    tooSmall: "Magnification must be at least 0.1",
    tooLarge: "Magnification cannot exceed 1000",
  },

  // Tray code errors
  trayCode: {
    invalid: "Tray code must be A, B, C, D, or E",
  },

  // Taxonomic field errors
  taxonomicField: {
    empty: "This field cannot be empty",
    tooLong: "This field is too long",
    invalidFormat:
      "Can only contain letters, numbers, spaces, hyphens, underscores, and periods",
  },

  // Sample ID errors
  sampleId: {
    empty: "Sample ID cannot be empty",
    tooLong: "Sample ID is too long",
    invalidFormat: "Sample ID can only contain letters, numbers, and dashes",
  },

  // Device ID errors
  deviceId: {
    empty: "Device ID cannot be empty",
    tooLong: "Device ID is too long",
    invalidUuid: "Please select a valid device",
  },

  // Image label errors
  imageLabel: {
    empty: "Image label cannot be empty",
    tooLong: "Image label is too long",
    invalidFormat:
      "Image label can only contain letters, numbers, spaces, hyphens, underscores, periods, commas, and parentheses",
  },

  // Class label errors
  classLabel: {
    empty: "Class label cannot be empty",
    tooLong: "Class label is too long",
    invalidFormat:
      "Class label can only contain letters, numbers, spaces, hyphens, and underscores",
  },

  // File validation errors
  file: {
    tooLarge: "File size must be less than 10MB",
    invalidType: "File must be a valid image format (PNG)",
    noneSelected: "At least one file must be selected",
    tooMany: "Cannot upload more than 100 files at once",
    allInvalid: "All files must be valid images under 10MB each",
  },

  // XSS protection errors
  xss: {
    htmlNotAllowed: "HTML tags are not allowed - please use plain text only",
    entitiesNotAllowed:
      "HTML entities are not allowed - please use plain text only",
    unsafeUrl: "Invalid or unsafe URL",
    unsafeContent: "Potentially unsafe content detected",
    unsafeProtocol: "Unsafe protocols are not allowed",
  },

  // Safe text errors
  safeText: {
    empty: "Text cannot be empty",
    emptyAfterTrim: "Text cannot be empty after trimming",
    tooLong: "Text is too long",
  },

  // Safe HTML errors
  safeHtml: {
    tooLong: "Content is too long",
  },

  // Safe URL errors
  safeUrl: {
    empty: "URL cannot be empty",
    tooLong: "URL is too long",
  },

  // Safe user input errors
  safeUserInput: {
    empty: "Input cannot be empty",
    emptyAfterTrim: "Input cannot be empty after trimming",
    tooLong: "Input is too long",
  },

  // Safe image label errors (with XSS protection)
  safeImageLabel: {
    htmlTagsNotAllowed: "HTML tags are not allowed in image labels",
    entitiesNotAllowed: "HTML entities are not allowed in image labels",
    unsafeProtocols: "Unsafe protocols are not allowed in image labels",
  },

  // Safe class label errors (with XSS protection)
  safeClassLabel: {
    htmlTagsNotAllowed: "HTML tags are not allowed in class labels",
    entitiesNotAllowed: "HTML entities are not allowed in class labels",
    unsafeProtocols: "Unsafe protocols are not allowed in class labels",
  },

  // Path validation errors
  path: {
    empty: "Path cannot be empty",
    invalidFormat:
      "Path can only contain alphanumeric, /, _, -, . and must end with alphanumeric",
    startsWithSlash: "Path cannot start with /",
    endsWithSlash: "Path cannot end with /",
    consecutiveSlashes: "Path cannot contain consecutive slashes",
  },

  // Generic Zod error messages (fallback for unmapped errors)
  generic: {
    required: "This field is required",
    invalid: "Invalid value",
    invalidType: "Expected {{expected}}, received {{received}}",
    tooSmall: "Must be at least {{minimum}}",
    tooLarge: "Must be at most {{maximum}}",
    tooSmallString: "Must be at least {{minimum}} characters",
    tooLargeString: "Must be at most {{maximum}} characters",
    notInteger: "Must be a whole number",
    notNumber: "Must be a number",
    invalidString: "Invalid format",
    invalidEnum: "Invalid selection",
    custom: "Validation error",
  },
} as const;

export default validation;
