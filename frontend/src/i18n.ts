import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Import translations
import enCommon from "./locales/en/common";
import enHeader from "./locales/en/header";
import enFooter from "./locales/en/footer";
import enPopups from "./locales/en/popups";
import enMain from "./locales/en/main";
import enValidation from "./locales/en/validation";
import enErrors from "./locales/en/errors";

import frCommon from "./locales/fr/common";
import frHeader from "./locales/fr/header";
import frFooter from "./locales/fr/footer";
import frPopups from "./locales/fr/popups";
import frMain from "./locales/fr/main";
import frValidation from "./locales/fr/validation";
import frErrors from "./locales/fr/errors";

// Translation resources
const resources = {
  en: {
    common: enCommon,
    header: enHeader,
    footer: enFooter,
    popups: enPopups,
    main: enMain,
    validation: enValidation,
    errors: enErrors,
  },
  fr: {
    common: frCommon,
    header: frHeader,
    footer: frFooter,
    popups: frPopups,
    main: frMain,
    validation: frValidation,
    errors: frErrors,
  },
} as const;

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: "en",
    supportedLngs: ["en", "fr"],
    defaultNS: "common",

    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "i18nextLng",
    },

    interpolation: {
      escapeValue: false, // React already escapes by default
    },

    debug: false, // Set to true for debugging
  });

export default i18n;
