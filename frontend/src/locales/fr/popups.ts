// Traductions des composants de fenêtres contextuelles et dialogues
const popups = {
  // Étiquettes de boutons communs utilisés dans plusieurs fenêtres contextuelles
  common: {
    save: "Enregistrer",
    cancel: "Annuler",
  },

  // Fenêtre d'authentification
  auth: {
    title: "Authentification requise",
    message: "Veuillez vous connecter pour accéder à l'application",
    signInButton: "SE CONNECTER",
    signingIn: "Connexion en cours...",
  },

  // Fenêtre Creative Commons
  creativeCommons: {
    title: "Utilisation d'images Creative Commons",
    introduction: {
      heading: "Introduction",
      text: "En téléversant vos images vers l'interface de classification des graines, vous acceptez de licencier votre travail sous une licence Creative Commons Attribution-Partage dans les mêmes conditions (CC BY-SA). Cet accord décrit les termes et conditions de la licence et d'autres considérations.",
    },
    termsAndConditions: {
      heading: "Termes et conditions",
      attribution:
        "Attribution : Vous permettez aux autres de copier, distribuer, afficher et exécuter votre œuvre protégée par le droit d'auteur—et les œuvres dérivées basées sur celle-ci—mais seulement s'ils vous accordent le crédit approprié en citant votre nom et la source.",
      shareAlike:
        "Partage dans les mêmes conditions : Vous permettez aux autres de distribuer des œuvres dérivées uniquement sous une licence identique à la licence qui régit votre œuvre.",
      machineLearning:
        "Apprentissage automatique : Vous accordez à l'ACIA le droit d'utiliser vos images pour entraîner des modèles d'apprentissage automatique. Ces modèles peuvent être utilisés à diverses fins, y compris la recherche, l'analyse et les activités commerciales.",
      warranty:
        "Garantie : Vous déclarez et garantissez que vous êtes le propriétaire légal du contenu que vous téléversez et qu'il n'enfreint aucun droit d'auteur, marque de commerce ou autres droits de tiers.",
      consent:
        "Consentement : Si votre image comprend des personnes identifiables, vous affirmez avoir obtenu leur consentement pour que l'image soit partagée et utilisée selon ces termes.",
      waiver:
        "Renonciation : L'image est fournie « telle quelle ». Vous renoncez à toutes les garanties, y compris celles concernant l'exactitude de l'image ou son adéquation à un usage particulier.",
    },
    acknowledgment: {
      heading: "Reconnaissance",
      text: "En cliquant sur « J'accepte », vous confirmez que vous avez lu et compris cet accord, et vous serez légalement lié par ses termes et conditions.",
    },
    agreeButton: "J'accepte",
    disagreeButton: "Je n'accepte pas",
  },

  // Fenêtre de métadonnées d'échantillon
  deviceInfo: {
    title: "Métadonnées d'échantillon",
    brand: "Marque",
    model: "Modèle",
    lens: "Lentille",
    doneButton: "Terminé",
    saveButton: "Enregistrer",
    cancelButton: "Annuler",
    // Champs de sélection d'appareil (composant partagé)
    deviceBrandLabel: "Marque de l'appareil",
    deviceModelLabel: "Modèle de l'appareil",
    deviceLensLabel: "Lentille de l'appareil",
    selectBrand: "Sélectionner une marque",
    selectModel: "Sélectionner un modèle",
    selectLens: "Sélectionner une lentille",
    none: "Aucun",
    errors: {
      brandRequired: "La marque de l'appareil est requise",
      modelRequired: "Le modèle de l'appareil est requis",
      lensRequired: "La lentille de l'appareil est requise",
    },
    validation: {
      invalidMagnification: "Le grossissement doit être un nombre positif",
      magnification: {
        tooSmall: "Le grossissement doit être d'au moins 0,1",
        tooLarge: "Le grossissement ne peut pas dépasser 1000",
      },
      imageName: {
        empty: "Le préfixe d'identifiant d'échantillon est requis",
        tooLong: "Le préfixe d'identifiant d'échantillon est trop long",
      },
      description: {
        empty: "La description de l'échantillon est requise",
        tooLong: "La description de l'échantillon est trop longue",
      },
    },
  },

  // Messages de validation partagés utilisés par les popups (voir useZodFieldValidation)
  validation: {
    invalidMagnification: "Le grossissement doit être un nombre positif",
    magnification: {
      tooSmall: "Le grossissement doit être d'au moins 0,1",
      tooLarge: "Le grossissement ne peut pas dépasser 1000",
    },
    imageName: {
      empty: "Le préfixe d'identifiant d'échantillon est requis",
      tooLong: "Le préfixe d'identifiant d'échantillon est trop long",
    },
    description: {
      empty: "La description de l'échantillon est requise",
      tooLong: "La description de l'échantillon est trop longue",
    },
  },

  // Fenêtre de métadonnées d'image
  imageMetadata: {
    title: "Modifier les métadonnées de l'image",
    imageName: "Nom de l'image",
    imageId: "ID de l'image",
    saveButton: "Enregistrer",
    cancelButton: "Annuler",
    errors: {
      imageNameRequired: "Le nom de l'image est requis",
    },
  },

  // Fenêtre de sélection du modèle
  modelSelection: {
    title: "Sélection du modèle de classification",
    subtitle: "Sélection du modèle :",
    date: "Date : {{date}}",
    version: "Version : {{version}}",
    doneButton: "Terminé",
    saveButton: "Enregistrer",
    cancelButton: "Annuler",
  },

  // Fenêtre d'enregistrement de capture
  saveCapture: {
    title: "Enregistrer la capture",
    captureTab: "CAPTURE",
    cacheTab: "CACHE",
    captureNameLabel: "Nom de la capture",
    captureNameError:
      "Le nom de la capture doit contenir au moins 3 caractères",
    formatPng: "Format : PNG",
    formatJpeg: "Format : JPEG",
    saveButton: "ENREGISTRER",
    cancelButton: "ANNULER",
  },

  // Fenêtre de téléversement d'image
  uploadImage: {
    title: "Charger une image",
    chooseFileButton: "Choisir un fichier",
  },

  // Champs taxonomiques (composant partagé utilisé dans le téléversement par lot et le formulaire de rétroaction)
  taxonomicFields: {
    familyLabel: "Famille",
    genusLabel: "Genre",
    speciesLabel: "Espèce",
    nameCodeLabel: "Code du nom",
  },

  // Fenêtre de téléversement par lot
  batchUpload: {
    title: "Téléversement d'images par lot",
    folderSection: {
      heading: "Informations sur le dossier",
      folderNameLabel: "Nom du dossier",
      folderNamePlaceholder: "p. ex., avena-fatua",
      folderNameHelper:
        "Seulement lettres, chiffres, points, tirets et traits de soulignement. Ne peut pas se terminer par un tiret ou trait de soulignement. Auto-normalisé en perdant le focus. S'il n'est pas fourni, sera généré automatiquement à partir du genre-espèce.",
      folderDescriptionLabel: "Description (facultative)",
      folderDescriptionPlaceholder:
        "p. ex., Collection d'échantillons de l'essai au champ 2025",
      folderDescriptionHelper:
        "Seulement lettres, chiffres, points et espaces. Pas d'espaces ou de points consécutifs. Auto-normalisé en perdant le focus.",
    },
    taxonomySection: {
      heading: "Informations taxonomiques",
      familyLabel: "Famille",
      familyPlaceholder: "Sélectionner ou saisir le nom de la famille",
      genusLabel: "Genre",
      genusPlaceholder: "Sélectionner ou saisir le nom du genre",
      speciesLabel: "Espèce",
      speciesPlaceholder: "Sélectionner ou saisir le nom de l'espèce",
      nameCodeLabel: "Code du nom",
      nameCodePlaceholder: "Sélectionner le code du nom",
    },
    metadataSection: {
      heading: "Métadonnées de l'échantillon",
      trayCodeLabel: "Code du plateau",
      trayCodePlaceholder: "Entrer le code du plateau",
      selectTrayCode: "Sélectionner le code du plateau",
      trayCodeRequired: "Le code du plateau est requis",
      sampleIdLabel: "Préfixe d'ID d'échantillon",
      sampleIdPlaceholder: "Entrer le préfixe (lettres, chiffres, tirets)",
      sampleIdHelper:
        "Seulement lettres, chiffres et tirets. Ne peut pas se terminer par un tiret. Auto-normalisé en perdant le focus.",
      sampleIdRequired: "Le préfixe d'ID d'échantillon est requis",
      sampleDescriptionLabel: "Description de l'échantillon",
      sampleDescriptionPlaceholder:
        "p. ex., Échantillon d'essai au champ de l'emplacement A",
      sampleDescriptionHelper:
        "Seulement lettres, chiffres, points et espaces. Pas d'espaces ou de points consécutifs. Auto-normalisé en perdant le focus.",
      sampleDescriptionRequired: "La description de l'échantillon est requise",
      magnificationRequired: "Le grossissement est requis",
      none: "Aucun",
    },
    deviceSection: {
      heading: "Informations sur l'appareil",
      magnificationLabel: "Grossissement",
      magnificationPlaceholder: "p. ex., 5, 10, 20",
    },
    folderActions: {
      createButton: "Créer un dossier",
      creatingButton: "Création en cours...",
      createdButton: "Dossier créé",
    },
    filesSection: {
      heading: "Fichiers",
      selectFiles: "Sélectionner des fichiers",
      filesSelected: "{{count}} fichier(s) sélectionné(s)",
      noFilesSelected: "Aucun fichier sélectionné",
      uploadStatus: "État du téléversement",
    },
    uploadSection: {
      uploadButton: "Téléverser",
      uploadingButton: "Téléversement en cours...",
      cancelButton: "Annuler",
      closeButton: "Fermer",
    },
    queue: {
      heading: "File de téléversement",
      queued: "En file ({{position}})",
      processing: "Traitement en cours...",
      completed: "Terminé",
      failed: "Échoué",
      pending: "En attente",
      progress: "{{completed}}/{{total}} fichiers téléversés",
      errorMessage: "Erreur : {{message}}",
    },
    validation: {
      folderNameRequired: "Le nom du dossier est requis",
      familyRequired: "La famille est requise",
      genusRequired: "Le genre est requis",
      speciesRequired: "L'espèce est requise",
      filesRequired: "Veuillez sélectionner au moins un fichier",
      invalidMagnification: "Le grossissement doit être un nombre positif",
      magnification: {
        tooSmall: "Le grossissement doit être d'au moins 0,1",
        tooLarge: "Le grossissement ne peut pas dépasser 1000",
      },
      imageName: {
        empty: "Le préfixe d'identifiant d'échantillon est requis",
        tooLong: "Le préfixe d'identifiant d'échantillon est trop long",
      },
      description: {
        empty: "La description de l'échantillon est requise",
        tooLong: "La description de l'échantillon est trop longue",
      },
    },
  },

  // Fenêtre de création de répertoire
  createDirectory: {
    titleCreate: "Créer un nouveau répertoire",
    titleEdit: "Modifier le répertoire",
    directoryNameLabel: "Nom du répertoire",
    directoryNameHelper:
      "Seulement lettres, chiffres, points, tirets et traits de soulignement. Ne peut pas se terminer par un tiret ou trait de soulignement. Auto-normalisé en perdant le focus.",
    directoryNamePlaceholder: "p. ex., avena-fatua ou echantillons-mycologie",
    descriptionLabel: "Description",
    descriptionHelper:
      "Seulement lettres, chiffres, points et espaces. Pas d'espaces ou de points consécutifs. Auto-normalisé en perdant le focus.",
    descriptionPlaceholder:
      "p. ex., Collection d'échantillons de l'essai au champ 2025",
    createButton: "Créer",
    updateButton: "Mettre à jour",
    cancelButton: "Annuler",
    errors: {
      signInRequired: "Vous devez être connecté pour créer un répertoire",
      authInProgress: "Authentification en cours, veuillez patienter",
      createFailed:
        "Erreur lors de la création du répertoire, voir la console pour plus de détails",
      updateFailed:
        "Erreur lors de la mise à jour du répertoire, voir la console pour plus de détails",
    },
  },

  // Fenêtre de suppression de répertoire
  deleteDirectory: {
    title: "Supprimer le répertoire",
    confirmMessage: "Êtes-vous sûr de vouloir supprimer {{folderName}} ?",
    deleteButton: "Supprimer",
    cancelButton: "Annuler",
    errors: {
      signInRequired: "Vous devez être connecté pour supprimer un répertoire",
      authInProgress: "Authentification en cours, veuillez patienter",
      noSelection: "Aucun répertoire sélectionné pour la suppression",
      deleteFailed:
        "Erreur lors de la suppression du répertoire, voir la console pour plus de détails",
    },
  },

  // Formulaire de rétroaction
  feedbackForm: {
    simple: {
      title: "Fournir une rétroaction",
    },
    negative: {
      title: "Rétroaction",
      boundingBox: {
        heading: "Boîte englobante",
        topX: "HautX",
        topY: "HautY",
        bottomX: "BasX",
        bottomY: "BasY",
      },
      reasonLabel: "Raison",
      reasons: {
        seedNotDetected: "Graine non détectée",
        wrongSeed: "Mauvaise graine",
        noSeed: "Aucune graine",
        multiSeed: "Plusieurs graines",
        wrongSeedNotInList: "Mauvaise graine non dans la liste",
      },
      familyLabel: "Famille",
      genusLabel: "Genre",
      speciesLabel: "Espèce",
      nameCodeLabel: "Code du nom",
      submitButton: "Soumettre",
      cancelButton: "Annuler",
      dragToggleButton: "Activer/Désactiver le déplacement/redimensionnement",
      saveBoxButton: "Enregistrer la boîte",
      boxSaved: "Modifications de la boîte enregistrées",
    },
  },

  // Fenêtre d'état d'inscription
  registrationStatus: {
    title: "Inscription du compte requise",
    message:
      "Votre compte n'est pas encore enregistré dans le système. Veuillez contacter votre administrateur système pour demander l'accès.",
    instruction:
      "Fournissez l'identifiant utilisateur suivant à votre administrateur :",
    copyTooltip: "Copier dans le presse-papiers",
    copiedMessage: "Copié dans le presse-papiers !",
    closeButton: "Fermer",
  },

  // Fenêtre de changement d'appareil
  switchDevice: {
    title: "Choisir l'appareil multimédia",
    save: "Enregistrer",
    cancel: "Annuler",
  },

  // Fenêtre du journal des notifications
  notifications: {
    title: "Journal des erreurs",
    emptyState: "Aucune erreur à afficher",
    clearAll: "Tout effacer",
    closeButton: "Fermer",
    justNow: "À l'instant",
    minutesAgo: "Il y a {{count}} minute(s)",
    hoursAgo: "Il y a {{count}} heure(s)",
    daysAgo: "Il y a {{count}} jour(s)",
  },
} as const;

export default popups;
