// Traductions communes partagées dans l'application
const common = {
  actions: {
    save: "Enregistrer",
    cancel: "Annuler",
    close: "Fermer",
    delete: "Supprimer",
    edit: "Modifier",
    add: "Ajouter",
    remove: "Retirer",
    confirm: "Confirmer",
    yes: "Oui",
    no: "Non",
    ok: "OK",
    select: "Sélectionner",
    choose: "Choisir",
    upload: "Téléverser",
    download: "Télécharger",
  },
  status: {
    loading: "Chargement...",
    processing: "Traitement en cours...",
    complete: "Terminé",
    success: "Succès",
    error: "Erreur",
    warning: "Avertissement",
    info: "Info",
  },
  form: {
    required: "Requis",
    optional: "Optionnel",
  },
} as const;

export default common;
