export const errors = {
  auth: {
    signInRequired: "Vous devez être connecté pour effectuer une inférence",
    signInRequiredUpload:
      "Vous devez être connecté pour télécharger des fichiers",
    inProgress: "Authentification en cours, veuillez patienter",
  },
  directory: {
    notSelected: "Veuillez sélectionner un répertoire",
  },
  inference: {
    fetchFailed:
      "Erreur lors de la récupération des données d'inférence, voir la console pour plus de détails",
    processingFailed:
      "Erreur lors du traitement de l'inférence, voir la console pour plus de détails",
  },
  queue: {
    full: "La file d'attente est pleine (10 éléments maximum). Veuillez attendre que certains se terminent.",
  },
  registration: {
    checkFailed:
      "Erreur lors de la vérification du statut d'inscription, voir la console pour plus de détails",
  },
  storage: {
    readFailed:
      "Erreur lors de la lecture du répertoire de stockage Azure, voir la console pour plus de détails",
  },
  save: {
    imageFailed: "Erreur lors de l'enregistrement de l'image : {{error}}",
  },
  boundary: {
    title: "Une erreur s'est produite",
    message:
      "Une erreur inattendue s'est produite. Notre équipe a été informée et nous travaillons à résoudre le problème.",
    devDetails: "Détails de l'erreur (développement uniquement) :",
    tryAgain: "Réessayer",
    goHome: "Retour à l'accueil",
    errorId: "ID d'erreur : {{errorId}}",
  },
} as const;

export type ErrorsTranslation = typeof errors;
export default errors;
