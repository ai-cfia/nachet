import "react-i18next";
import type enCommon from "./en/common";
import type enHeader from "./en/header";
import type enFooter from "./en/footer";
import type enMain from "./en/main";

declare module "react-i18next" {
  interface CustomTypeOptions {
    defaultNS: "common";
    resources: {
      common: typeof enCommon;
      header: typeof enHeader;
      footer: typeof enFooter;
      main: typeof enMain;
    };
  }
}
