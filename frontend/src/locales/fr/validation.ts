// Traductions des messages d'erreur de validation (Français)
const validation = {
  // Erreurs de nom de répertoire
  directoryName: {
    empty: "Le nom du répertoire ne peut pas être vide",
    tooLong: "Le nom du répertoire est trop long",
    invalidFormat:
      "Le nom du répertoire doit contenir uniquement des lettres, des chiffres, des traits d'union et des traits de soulignement, et ne peut pas commencer ou se terminer par un trait d'union ou un trait de soulignement",
  },

  // Erreurs d'email
  email: {
    required: "L'adresse courriel est requise",
    invalid: "Veuillez entrer une adresse courriel valide",
    tooLong: "L'adresse courriel est trop longue",
  },

  // Erreurs de mot de passe
  password: {
    tooShort: "Le mot de passe doit contenir au moins 8 caractères",
    tooLong: "Le mot de passe est trop long",
    weakPassword:
      "Le mot de passe doit contenir au moins une lettre majuscule, une lettre minuscule et un chiffre",
  },

  // Erreurs de nom de dossier
  folderName: {
    tooLong: "Le nom du dossier est trop long",
    invalidFormat:
      "Le nom du dossier ne peut contenir que des lettres, des chiffres, des traits d'union et des traits de soulignement",
  },

  // Erreurs de nombre de graines
  seedCount: {
    notInteger: "Le nombre de graines doit être un nombre entier",
    tooSmall: "Le nombre de graines doit être d'au moins 1",
    tooLarge: "Le nombre de graines ne peut pas dépasser 100",
  },

  // Erreurs de niveau de zoom
  zoomLevel: {
    tooSmall: "Le niveau de zoom doit être d'au moins 0,1",
    tooLarge: "Le niveau de zoom ne peut pas dépasser 100",
  },

  // Erreurs de grossissement
  magnification: {
    tooSmall: "Le grossissement doit être d'au moins 0,1",
    tooLarge: "Le grossissement ne peut pas dépasser 1000",
  },

  // Erreurs de code de plateau
  trayCode: {
    invalid: "Le code du plateau doit être A, B, C, D ou E",
  },

  // Erreurs de champ taxonomique
  taxonomicField: {
    empty: "Ce champ ne peut pas être vide",
    tooLong: "Ce champ est trop long",
    invalidFormat:
      "Ne peut contenir que des lettres, des chiffres, des espaces, des traits d'union, des traits de soulignement et des points",
  },

  // Erreurs d'identifiant d'échantillon
  sampleId: {
    empty: "L'identifiant d'échantillon ne peut pas être vide",
    tooLong: "L'identifiant d'échantillon est trop long",
    invalidFormat:
      "L'identifiant d'échantillon ne peut contenir que des lettres, des chiffres et des traits d'union",
  },

  // Erreurs d'identifiant d'appareil
  deviceId: {
    empty: "L'identifiant d'appareil ne peut pas être vide",
    tooLong: "L'identifiant d'appareil est trop long",
    invalidUuid: "Veuillez sélectionner un appareil valide",
  },

  // Erreurs d'étiquette d'image
  imageLabel: {
    empty: "L'étiquette d'image ne peut pas être vide",
    tooLong: "L'étiquette d'image est trop longue",
    invalidFormat:
      "L'étiquette d'image ne peut contenir que des lettres, des chiffres, des espaces, des traits d'union, des traits de soulignement, des points, des virgules et des parenthèses",
  },

  // Erreurs d'étiquette de classe
  classLabel: {
    empty: "L'étiquette de classe ne peut pas être vide",
    tooLong: "L'étiquette de classe est trop longue",
    invalidFormat:
      "L'étiquette de classe ne peut contenir que des lettres, des chiffres, des espaces, des traits d'union et des traits de soulignement",
  },

  // Erreurs de validation de fichier
  file: {
    tooLarge: "La taille du fichier doit être inférieure à 10 Mo",
    invalidType: "Le fichier doit être un format d'image valide (PNG)",
    noneSelected: "Au moins un fichier doit être sélectionné",
    tooMany: "Impossible de téléverser plus de 100 fichiers à la fois",
    allInvalid:
      "Tous les fichiers doivent être des images valides de moins de 10 Mo chacune",
  },

  // Erreurs de protection XSS
  xss: {
    htmlNotAllowed:
      "Les balises HTML ne sont pas autorisées - veuillez utiliser du texte brut uniquement",
    entitiesNotAllowed:
      "Les entités HTML ne sont pas autorisées - veuillez utiliser du texte brut uniquement",
    unsafeUrl: "URL invalide ou non sécurisée",
    unsafeContent: "Contenu potentiellement non sécurisé détecté",
    unsafeProtocol: "Les protocoles non sécurisés ne sont pas autorisés",
  },

  // Erreurs de texte sécurisé
  safeText: {
    empty: "Le texte ne peut pas être vide",
    emptyAfterTrim:
      "Le texte ne peut pas être vide après suppression des espaces",
    tooLong: "Le texte est trop long",
  },

  // Erreurs de HTML sécurisé
  safeHtml: {
    tooLong: "Le contenu est trop long",
  },

  // Erreurs d'URL sécurisée
  safeUrl: {
    empty: "L'URL ne peut pas être vide",
    tooLong: "L'URL est trop longue",
  },

  // Erreurs d'entrée utilisateur sécurisée
  safeUserInput: {
    empty: "L'entrée ne peut pas être vide",
    emptyAfterTrim:
      "L'entrée ne peut pas être vide après suppression des espaces",
    tooLong: "L'entrée est trop longue",
  },

  // Erreurs d'étiquette d'image sécurisée (avec protection XSS)
  safeImageLabel: {
    htmlTagsNotAllowed:
      "Les balises HTML ne sont pas autorisées dans les étiquettes d'image",
    entitiesNotAllowed:
      "Les entités HTML ne sont pas autorisées dans les étiquettes d'image",
    unsafeProtocols:
      "Les protocoles non sécurisés ne sont pas autorisés dans les étiquettes d'image",
  },

  // Erreurs d'étiquette de classe sécurisée (avec protection XSS)
  safeClassLabel: {
    htmlTagsNotAllowed:
      "Les balises HTML ne sont pas autorisées dans les étiquettes de classe",
    entitiesNotAllowed:
      "Les entités HTML ne sont pas autorisées dans les étiquettes de classe",
    unsafeProtocols:
      "Les protocoles non sécurisés ne sont pas autorisés dans les étiquettes de classe",
  },

  // Erreurs de validation de chemin
  path: {
    empty: "Le chemin ne peut pas être vide",
    invalidFormat:
      "Le chemin ne peut contenir que des caractères alphanumériques, /, _, -, . et doit se terminer par un caractère alphanumérique",
    startsWithSlash: "Le chemin ne peut pas commencer par /",
    endsWithSlash: "Le chemin ne peut pas se terminer par /",
    consecutiveSlashes:
      "Le chemin ne peut pas contenir de barres obliques consécutives",
  },

  // Messages d'erreur Zod génériques (repli pour les erreurs non mappées)
  generic: {
    required: "Ce champ est requis",
    invalid: "Valeur invalide",
    invalidType: "Type attendu {{expected}}, reçu {{received}}",
    tooSmall: "Doit être au moins {{minimum}}",
    tooLarge: "Doit être au maximum {{maximum}}",
    tooSmallString: "Doit contenir au moins {{minimum}} caractères",
    tooLargeString: "Doit contenir au maximum {{maximum}} caractères",
    notInteger: "Doit être un nombre entier",
    notNumber: "Doit être un nombre",
    invalidString: "Format invalide",
    invalidEnum: "Sélection invalide",
    custom: "Erreur de validation",
  },
} as const;

export default validation;
