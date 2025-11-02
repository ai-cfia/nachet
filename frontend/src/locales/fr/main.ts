// Traductions des composants principaux de l'application
const main = {
  // Contrôles MicroscopeFeed
  microscopeFeed: {
    controls: {
      deviceLabel: "APPAREIL",
      captureLabel: "CAPTURER",
      loadLabel: "CHARGER",
      saveLabel: "ENREGISTRER",
      batchLabel: "LOT",
      classifyLabel: "CLASSIFIER",
      directLabel: "D", // Bouton d'inférence directe pour les membres
      annotateLabel: "ANNOTER",
      switchLabel: "CHANGER",
    },
    workspace: {
      processingTooltip: "Traitement en cours...",
      queuePositionTooltip: "Position dans la file {{position}}",
      resultsAvailableTooltip: "Résultats disponibles",
    },
    errors: {
      signInRequired: "Vous devez être connecté pour soumettre une rétroaction",
      authInProgress: "Authentification en cours, veuillez patienter",
    },
  },

  // Résultats de classification
  classificationResults: {
    title: "RÉSULTATS",
    topResults: "Meilleurs résultats",
  },

  // Cache d'images
  imageCache: {
    title: "CAPTURES",
    captureLabel: "Capture {{index}}",
  },

  // Liste de répertoires
  directoryList: {
    title: "RÉPERTOIRES",
  },
} as const;

export default main;
