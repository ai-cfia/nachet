// Popup and dialog component translations
const popups = {
  // Common button labels used across multiple popups
  common: {
    save: "Save",
    cancel: "Cancel",
  },

  // Authentication Popup
  auth: {
    title: "Authentication Required",
    message: "Please sign in to access the application",
    signInButton: "SIGN IN",
    signingIn: "Signing in...",
  },

  // Creative Commons Popup
  creativeCommons: {
    title: "Use of Creative Commons Images",
    introduction: {
      heading: "Introduction",
      text: "By uploading your images to Seed Classification Interface, you agree to license your work under a Creative Commons Attribution-ShareAlike (CC BY-SA) License. This agreement outlines the terms and conditions of the license and other considerations.",
    },
    termsAndConditions: {
      heading: "Terms and Conditions",
      attribution:
        "Attribution: You allow others to copy, distribute, display, and perform your copyrighted work—and derivative works based upon it—but only if they give you the proper credit by citing your name and the source.",
      shareAlike:
        "Share Alike: You allow others to distribute derivative works only under a license identical to the license that governs your work.",
      machineLearning:
        "Machine Learning: You grant the CFIA the right to use your images to train machine learning models. These models may be used for various purposes, including research, analysis, and commercial activities.",
      warranty:
        "Warranty: You represent and warrant that you are the legal owner of the content you are uploading and that it does not infringe on any copyright, trademark, or other rights of third parties.",
      consent:
        "Consent: If your image includes identifiable individuals, you affirm that you have obtained their consent for the image to be shared and used under these terms.",
      waiver:
        'Waiver: The image is provided "as-is." You waive all warranties, including any regarding the image\'s accuracy or fitness for a particular purpose.',
    },
    acknowledgment: {
      heading: "Acknowledgement",
      text: 'By clicking "I Agree," you confirm that you have read and understood this agreement, and you will be legally bound by its terms and conditions.',
    },
    agreeButton: "I Agree",
    disagreeButton: "I Disagree",
  },

  // Sample Metadata Popup
  deviceInfo: {
    title: "Sample Metadata",
    brand: "Brand",
    model: "Model",
    lens: "Lens",
    doneButton: "Done",
    saveButton: "Save",
    cancelButton: "Cancel",
    // Device Selection Fields (shared component)
    deviceBrandLabel: "Device Brand",
    deviceModelLabel: "Device Model",
    deviceLensLabel: "Device Lens",
    selectBrand: "Select a brand",
    selectModel: "Select a model",
    selectLens: "Select a lens",
    errors: {
      brandRequired: "Device brand is required",
      modelRequired: "Device model is required",
      lensRequired: "Device lens is required",
    },
  },

  // Image Metadata Popup
  imageMetadata: {
    title: "Edit Image Metadata",
    imageName: "Image Name",
    imageId: "Image ID",
    saveButton: "Save",
    cancelButton: "Cancel",
    errors: {
      imageNameRequired: "Image name is required",
    },
  },

  // Model Selection Popup
  modelSelection: {
    title: "Classification Model Selection",
    subtitle: "Model Selection:",
    date: "Date: {{date}}",
    version: "Version: {{version}}",
    doneButton: "Done",
    saveButton: "Save",
    cancelButton: "Cancel",
  },

  // Save Capture Popup
  saveCapture: {
    title: "Save Capture",
    captureTab: "CAPTURE",
    cacheTab: "CACHE",
    captureNameLabel: "Capture Name",
    captureNameError: "Capture name must be at least 3 characters long",
    formatPng: "Format: PNG",
    formatJpeg: "Format: JPEG",
    saveButton: "SAVE",
    cancelButton: "CANCEL",
  },

  // Upload Image Popup
  uploadImage: {
    title: "Load Image",
    chooseFileButton: "Choose File",
  },

  // Taxonomic Fields (shared component used in batch upload and feedback form)
  taxonomicFields: {
    familyLabel: "Family",
    genusLabel: "Genus",
    speciesLabel: "Species",
    nameCodeLabel: "Name Code",
  },

  // Batch Upload Popup
  batchUpload: {
    title: "Batch Upload Images",
    folderSection: {
      heading: "Folder Information",
      folderNameLabel: "Folder Name",
      folderNamePlaceholder: "e.g., avena-fatua",
      folderNameHelper:
        "Only letters, numbers, periods, hyphens, and underscores. Cannot end with dash or underscore. Auto-normalized on blur. If not provided, will be auto-generated from genus-species.",
      folderDescriptionLabel: "Description (Optional)",
      folderDescriptionPlaceholder:
        "e.g., Sample collection from field trial 2025",
      folderDescriptionHelper:
        "Only letters, numbers, periods, and spaces. No consecutive spaces or periods. Auto-normalized on blur.",
    },
    taxonomySection: {
      heading: "Taxonomy Information",
      familyLabel: "Family",
      familyPlaceholder: "Select or type family name",
      genusLabel: "Genus",
      genusPlaceholder: "Select or type genus name",
      speciesLabel: "Species",
      speciesPlaceholder: "Select or type species name",
      nameCodeLabel: "Name Code",
      nameCodePlaceholder: "Select name code",
    },
    metadataSection: {
      heading: "Sample Metadata",
      trayCodeLabel: "Tray Code",
      trayCodePlaceholder: "Enter tray code",
      selectTrayCode: "Select Tray Code",
      trayCodeRequired: "Tray code is required",
      sampleIdLabel: "Sample ID Prefix",
      sampleIdPlaceholder: "Enter prefix (letters, numbers, dashes)",
      sampleIdHelper:
        "Only letters, numbers, and dashes. Cannot end with a dash. Auto-normalized on blur.",
      sampleIdRequired: "Sample ID prefix is required",
      sampleDescriptionLabel: "Sample Description",
      sampleDescriptionPlaceholder: "e.g., Field trial sample from location A",
      sampleDescriptionHelper:
        "Only letters, numbers, periods, and spaces. No consecutive spaces or periods. Auto-normalized on blur.",
      sampleDescriptionRequired: "Sample description is required",
      magnificationRequired: "Magnification is required",
    },
    deviceSection: {
      heading: "Device Information",
      magnificationLabel: "Magnification",
      magnificationPlaceholder: "e.g., 5, 10, 20",
    },
    folderActions: {
      createButton: "Create Folder",
      creatingButton: "Creating...",
      createdButton: "Folder Created",
    },
    filesSection: {
      heading: "Files",
      selectFiles: "Select Files",
      filesSelected: "{{count}} file(s) selected",
      noFilesSelected: "No files selected",
      uploadStatus: "Upload Status",
    },
    uploadSection: {
      uploadButton: "Upload",
      uploadingButton: "Uploading...",
      cancelButton: "Cancel",
      closeButton: "Close",
    },
    queue: {
      heading: "Upload Queue",
      queued: "Queued ({{position}})",
      processing: "Processing...",
      completed: "Completed",
      failed: "Failed",
      pending: "Pending",
      progress: "{{completed}}/{{total}} files uploaded",
      errorMessage: "Error: {{message}}",
    },
    validation: {
      folderNameRequired: "Folder name is required",
      familyRequired: "Family is required",
      genusRequired: "Genus is required",
      speciesRequired: "Species is required",
      filesRequired: "Please select at least one file",
      invalidMagnification: "Magnification must be a positive number",
    },
  },

  // Create Directory Popup
  createDirectory: {
    titleCreate: "Create New Directory",
    titleEdit: "Edit Directory",
    directoryNameLabel: "Directory Name",
    directoryNameHelper:
      "Only letters, numbers, periods, hyphens, and underscores. Cannot end with dash or underscore. Auto-normalized on blur.",
    directoryNamePlaceholder: "e.g., avena-fatua or mycology-samples",
    descriptionLabel: "Description",
    descriptionHelper:
      "Only letters, numbers, periods, and spaces. No consecutive spaces or periods. Auto-normalized on blur.",
    descriptionPlaceholder: "e.g., Sample collection from field trial 2025",
    createButton: "Create",
    updateButton: "Update",
    cancelButton: "Cancel",
    errors: {
      signInRequired: "You must be signed in to create a directory",
      authInProgress: "Authentication in progress, please wait",
      createFailed: "Error creating directory, see console for more details",
      updateFailed: "Error updating directory, see console for more details",
    },
  },

  // Delete Directory Popup
  deleteDirectory: {
    title: "Delete Directory",
    confirmMessage: "Are you sure you want to delete {{folderName}}?",
    deleteButton: "Delete",
    cancelButton: "Cancel",
    errors: {
      signInRequired: "You must be signed in to delete a directory",
      authInProgress: "Authentication in progress, please wait",
      noSelection: "No directory selected to delete",
      deleteFailed: "Error deleting directory, see console for more details",
    },
  },

  // Feedback Form
  feedbackForm: {
    simple: {
      title: "Provide Feedback",
    },
    negative: {
      title: "Feedback",
      boundingBox: {
        heading: "Bounding Box",
        topX: "TopX",
        topY: "TopY",
        bottomX: "BottomX",
        bottomY: "BottomY",
      },
      reasonLabel: "Reason",
      reasons: {
        seedNotDetected: "Seed not Detected",
        wrongSeed: "Wrong Seed",
        noSeed: "No Seed",
        multiSeed: "Multi Seed",
        wrongSeedNotInList: "Wrong Seed not in List",
      },
      familyLabel: "Family",
      genusLabel: "Genus",
      speciesLabel: "Species",
      nameCodeLabel: "Name Code",
      submitButton: "Submit",
      cancelButton: "Cancel",
      dragToggleButton: "Toggle Drag/Resize",
      saveBoxButton: "Save Box",
      boxSaved: "Box changes saved",
    },
  },

  // Registration Status Popup
  registrationStatus: {
    title: "Account Registration Required",
    message:
      "Your account is not yet registered in the system. Please contact your system administrator to request access.",
    instruction: "Provide the following user ID to your administrator:",
    copyTooltip: "Copy to clipboard",
    copiedMessage: "Copied to clipboard!",
    closeButton: "Close",
  },

  // Switch Device Popup
  switchDevice: {
    title: "Choose Media Device",
    save: "Save",
    cancel: "Cancel",
  },

  // Notification Log Popup
  notifications: {
    title: "Error Log",
    emptyState: "No errors to display",
    clearAll: "Clear All",
    closeButton: "Close",
    justNow: "Just now",
    minutesAgo: "{{count}} minute(s) ago",
    hoursAgo: "{{count}} hour(s) ago",
    daysAgo: "{{count}} day(s) ago",
  },

  // Popup Validation Messages
  validation: {
    invalidMagnification: "Magnification must be a positive number",
    magnification: {
      tooSmall: "Magnification must be at least 0.1",
      tooLarge: "Magnification cannot exceed 1000",
    },
    imageName: {
      empty: "Sample ID prefix is required",
      tooLong: "Sample ID prefix is too long",
    },
    description: {
      empty: "Sample description is required",
      tooLong: "Sample description is too long",
    },
    // Fallback Zod issues messages
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
  },
} as const;

export default popups;
