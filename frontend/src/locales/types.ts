// TypeScript types for i18n translations
// This file provides type safety and autocomplete for translation keys

import "react-i18next";
import type enCommon from "./en/common";
import type enErrors from "./en/errors";
import type enFooter from "./en/footer";
import type enHeader from "./en/header";
import type enMain from "./en/main";
import type enPopups from "./en/popups";
import type enValidation from "./en/validation";

// Define the resources type based on English translations
declare module "react-i18next" {
  interface CustomTypeOptions {
    defaultNS: "common";
    resources: {
      common: typeof enCommon;
      header: typeof enHeader;
      footer: typeof enFooter;
      popups: typeof enPopups;
      main: typeof enMain;
      validation: typeof enValidation;
      errors: typeof enErrors;
    };
  }
}
