const main = {
  controls: {
    camera: "Cam\u00e9ra",
    noCamera: "Aucune cam\u00e9ra",
    cameraDevice: "Cam\u00e9ra {{id}}",
    capture: "Capturer",
    upload: "T\u00e9l\u00e9verser",
    imageMode: "Mode t\u00e9l\u00e9versement d'image",
    save: "Enregistrer",
    export: "Exporter",
    meta: "Méta",
    metadataRequired: "Définir les métadonnées par défaut d\u2019abord",
    runInference: "Identifier",
    editBoxes: "Modifier les bo\u00eetes",
    addBox: "Ajouter une bo\u00eete",
    discardEdits: "Annuler",
    deleteBox: "Supprimer",
  },
  status: {
    loadingModel: "Chargement du mod\u00e8le\u2026",
    detecting: "D\u00e9tection des objets\u2026",
    classifying: "Classification des d\u00e9tections\u2026",
    classifyingEdited: "Classification des bo\u00eetes modifi\u00e9es\u2026",
    inferenceComplete: "Inf\u00e9rence termin\u00e9e",
    modelReady: "Mod\u00e8le pr\u00eat",
    noModelLoaded: "Aucun mod\u00e8le charg\u00e9",
    cameraError: "Erreur de cam\u00e9ra\u00a0: {{message}}",
    error: "Erreur\u00a0: {{error}}",
  },
  modelLoader: {
    detector: "D\u00e9tecteur",
    classifier: "Classificateur",
    detectorInfo: "Voir les informations du mod\u00e8le d\u00e9tecteur",
    classifierInfo: "Voir les informations du mod\u00e8le classificateur",
    loadModel: "Charger le mod\u00e8le",
    loading: "Chargement\u2026",
  },
  imageUpload: {
    title: "T\u00e9l\u00e9verser des images",
    chooseFile: "Choisir des fichiers",
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
  exportDialog: {
    title: "Exporter les donn\u00e9es",
    summary:
      "{{imageCount}} images, {{resultCount}} r\u00e9sultats d\u2019inf\u00e9rence",
    nothingSelected: "Aucune image ou r\u00e9sultat s\u00e9lectionn\u00e9",
    includeImages: "Inclure les images",
    includeResults: "Inclure les r\u00e9sultats JSON",
    includeCsv: "Inclure le CSV",
    includeAnnotatedImages: "Inclure les images annotées",
    humanReadable: "Noms de fichiers lisibles",
    duplicateNameError:
      "Nom d'image en double : {{name}}. Renommez avant d'exporter.",
  },
  resultsTable: {
    title: "R\u00e9sultats de classification",
    topResults: "Meilleurs r\u00e9sultats",
    classifying: "Classification en cours...",
  },
  imageGallery: {
    title: "Images",
    image: "Image {{number}}",
    clearAllImages: "Effacer toutes les images",
    editMetadataImage: "Modifier les métadonnées de l’image {{number}}",
    selectImage: "Sélectionner l’image {{number}}",
    selectResult: "Sélectionner le résultat {{modelId}}",
    resultsAvailable: "R\u00e9sultats disponibles",
    resultEntry: "{{time}} \u2014 {{modelId}}",
    boxes: "{{count}} bo\u00eetes",
    removeResult: "Supprimer les r\u00e9sultats s\u00e9lectionn\u00e9s",
  },
  metadata: {
    defaultsTitle: "Métadonnées par défaut",
    imageTitle: "Métadonnées de l\u2019image",
    namePrefix: "Préfixe du nom",
    namePrefixHint: "Les captures seront nommées préfixe-1, préfixe-2, etc.",
    imageName: "Nom de l\u2019image",
    deviceBrand: "Marque de l\u2019appareil",
    deviceModel: "Modèle de l\u2019appareil",
    deviceLens: "Lentille de l\u2019appareil",
    trayCode: "Code du plateau",
    description: "Description",
    selectBrand: "Sélectionner la marque",
    selectModel: "Sélectionner le modèle",
    selectLens: "Sélectionner la lentille",
    selectTrayCode: "Sélectionner le code du plateau",
    save: "Enregistrer",
    cancel: "Annuler",
    validation: {
      imageNameRequired: "Le nom de l\u2019image est obligatoire",
      imageNameTooLong:
        "Le nom de l\u2019image ne doit pas dépasser 100 caractères",
      imageNameInvalid:
        "Seuls les lettres, chiffres, points et tirets sont autorisés",
      descriptionTooLong: "La description ne doit pas dépasser 1000 caractères",
      descriptionInvalid:
        "Seuls les lettres, chiffres, espaces et points sont autorisés",
    },
  },
  validation: {
    invalidType: "Le fichier doit \u00eatre une image PNG ou JPEG",
    fileTooLarge: "La taille du fichier ne doit pas d\u00e9passer 10\u00a0Mo",
    dimensionsTooLarge:
      "Les dimensions de l\u2019image ne doivent pas d\u00e9passer 4608\u00d72592 pixels",
    unreadableDimensions: "Impossible de lire les dimensions de l\u2019image",
    loadFailed: "Impossible de charger l\u2019image",
  },
  versionDialog: {
    title: "Nouvelle version disponible",
    message:
      "Une nouvelle version de nachet-mini est disponible. Vous utilisez la version {{current}}\u00a0; la derni\u00e8re est {{remote}}.",
    warning:
      "Le rechargement supprimera toute progression non enregistr\u00e9e. Exportez d\u2019abord vos donn\u00e9es si vous souhaitez les conserver.",
    reload: "Recharger",
  },
} as const;

export default main;
