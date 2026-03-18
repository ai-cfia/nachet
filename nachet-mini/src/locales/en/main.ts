const main = {
  controls: {
    camera: "Camera",
    noCamera: "No camera",
    cameraDevice: "Camera {{id}}",
    capture: "Capture",
    upload: "Upload",
    save: "Save",
    runInference: "Identify",
  },
  status: {
    loadingModel: "Loading model\u2026",
    detecting: "Detecting objects\u2026",
    classifying: "Classifying detections\u2026",
    inferenceComplete: "Inference complete",
    modelReady: "Model ready",
    noModelLoaded: "No model loaded",
    cameraError: "Camera error: {{message}}",
    error: "Error: {{error}}",
  },
  modelLoader: {
    detector: "Detector",
    classifier: "Classifier",
    loadModel: "Load Model",
    loading: "Loading\u2026",
  },
  imageUpload: {
    title: "Upload Image",
    chooseFile: "Choose File",
  },
  saveDialog: {
    title: "Save Image",
    currentImage: "Current Image",
    allImages: "All Images (ZIP)",
    imageName: "Image name",
    labelRequired: "Label is required",
    labelInvalid:
      "Only letters, numbers, spaces, dashes, underscores, and periods",
  },
  resultsTable: {
    title: "Classification Results",
    topResults: "Top results",
    classifying: "Classifying...",
  },
  imageGallery: {
    title: "Images",
    image: "Image {{number}}",
    resultsAvailable: "Results available",
    resultEntry: "{{modelId}}",
    boxes: "{{count}} boxes",
  },
  validation: {
    invalidType: "File must be a PNG or JPEG image",
    fileTooLarge: "File size must be less than 10MB",
    dimensionsTooLarge: "Image dimensions must not exceed 1920x1080 pixels",
    unreadableDimensions: "Unable to read image dimensions",
    loadFailed: "Failed to load image",
  },
} as const;

export default main;
