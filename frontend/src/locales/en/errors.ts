export const errors = {
  auth: {
    signInRequired: "You must be signed in to perform inference",
    signInRequiredUpload: "You must be signed in to upload files",
    inProgress: "Authentication in progress, please wait",
  },
  directory: {
    notSelected: "Please select a directory",
  },
  inference: {
    fetchFailed: "Error fetching inference data, see console for details",
    processingFailed:
      "Workflow {{workflowId}} failed for image {{imageId}}: {{error}}",
  },
  queue: {
    full: "Queue is full (10 items max). Please wait for some to complete.",
  },
  registration: {
    checkFailed: "Error checking registration status, see console for details",
  },
  storage: {
    readFailed:
      "Error reading Azure storage directory, see console for details",
  },
  save: {
    imageFailed: "Error saving image: {{error}}",
  },
  boundary: {
    title: "Something went wrong",
    message:
      "An unexpected error has occurred. Our team has been notified and we're working to fix the issue.",
    devDetails: "Error Details (Development Only):",
    tryAgain: "Try Again",
    goHome: "Go to Home",
    errorId: "Error ID: {{errorId}}",
  },
} as const;

export type ErrorsTranslation = typeof errors;
export default errors;
