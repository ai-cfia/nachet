// Main application component translations
const main = {
  // MicroscopeFeed Controls
  microscopeFeed: {
    controls: {
      deviceLabel: "META",
      captureLabel: "CAPTURE",
      loadLabel: "LOAD",
      saveLabel: "SAVE",
      batchLabel: "BATCH",
      notificationsLabel: "LOG",
      classifyLabel: "CLASSIFY",
      directLabel: "D", // Direct inference button for members
      annotateLabel: "ANNOTATE",
      switchLabel: "SWITCH",
    },
    workspace: {
      processingTooltip: "Processing...",
      queuePositionTooltip: "Queue position {{position}}",
      resultsAvailableTooltip: "Results available",
    },
    errors: {
      signInRequired: "You must be signed in to submit feedback",
      authInProgress: "Authentication in progress, please wait",
    },
  },

  // Classification Results
  classificationResults: {
    title: "RESULTS",
    topResults: "Top Results",
  },

  // Image Cache
  imageCache: {
    title: "CAPTURES",
    captureLabel: "Capture {{index}}",
  },

  // Directory List
  directoryList: {
    title: "DIRECTORIES",
  },
} as const;

export default main;
