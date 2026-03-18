const main = {
  controls: {
    camera: "Cam\u00e9ra",
    noCamera: "Aucune cam\u00e9ra",
    cameraDevice: "Cam\u00e9ra {{id}}",
    capture: "Capturer",
    upload: "T\u00e9l\u00e9verser",
    save: "Enregistrer",
    runInference: "Lancer l\u2019inf\u00e9rence",
  },
  status: {
    loadingModel: "Chargement du mod\u00e8le\u2026",
    detecting: "D\u00e9tection des objets\u2026",
    classifying: "Classification des d\u00e9tections\u2026",
    inferenceComplete: "Inf\u00e9rence termin\u00e9e",
    modelReady: "Mod\u00e8le pr\u00eat",
    noModelLoaded: "Aucun mod\u00e8le charg\u00e9",
    cameraError: "Erreur de cam\u00e9ra\u00a0: {{message}}",
    error: "Erreur\u00a0: {{error}}",
  },
  modelLoader: {
    detector: "D\u00e9tecteur",
    classifier: "Classificateur",
    loadModel: "Charger le mod\u00e8le",
    loading: "Chargement\u2026",
  },
  imageUpload: {
    title: "T\u00e9l\u00e9verser une image",
    chooseFile: "Choisir un fichier",
  },
  saveDialog: {
    title: "Enregistrer l\u2019image",
    currentImage: "Image actuelle",
    allImages: "Toutes les images (ZIP)",
    imageName: "Nom de l\u2019image",
    labelRequired: "Le libell\u00e9 est obligatoire",
    labelInvalid:
      "Seuls les lettres, chiffres, espaces, tirets, traits de soulignement et points sont autoris\u00e9s",
  },
  resultsTable: {
    title: "R\u00e9sultats de classification",
    topResults: "Meilleurs r\u00e9sultats",
    classifying: "Classification en cours...",
  },
  imageGallery: {
    title: "Images",
    image: "Image {{number}}",
    resultsAvailable: "R\u00e9sultats disponibles",
    resultEntry: "{{modelId}}",
    boxes: "{{count}} bo\u00eetes",
  },
  validation: {
    invalidType: "Le fichier doit \u00eatre une image PNG ou JPEG",
    fileTooLarge: "La taille du fichier ne doit pas d\u00e9passer 10\u00a0Mo",
    dimensionsTooLarge:
      "Les dimensions de l\u2019image ne doivent pas d\u00e9passer 1920\u00d71080 pixels",
    unreadableDimensions: "Impossible de lire les dimensions de l\u2019image",
    loadFailed: "Impossible de charger l\u2019image",
  },
} as const;

export default main;
