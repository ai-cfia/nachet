import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import enCommon from "./locales/en/common";
import enHeader from "./locales/en/header";
import enFooter from "./locales/en/footer";
import enMain from "./locales/en/main";

import frCommon from "./locales/fr/common";
import frHeader from "./locales/fr/header";
import frFooter from "./locales/fr/footer";
import frMain from "./locales/fr/main";

const resources = {
  en: {
    common: enCommon,
    header: enHeader,
    footer: enFooter,
    main: enMain,
  },
  fr: {
    common: frCommon,
    header: frHeader,
    footer: frFooter,
    main: frMain,
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
      escapeValue: false,
    },

    debug: false,
  });

export default i18n;
