import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locale/en.json";
import es from "./locale/es.json";

// https://www.i18next.com/overview/configuration-options
i18n.use(initReactI18next).init({
  debug: process.env.NODE_ENV === "development",
  supportedLngs: ["en", "es"],
  fallbackLng: "es",
  resources: {
    en: { translation: en },
    es: { translation: es },
  },
  // https://react.i18next.com/getting-started#basic-sample
  interpolation: {
    escapeValue: false,
  },
  // https://www.i18next.com/overview/getting-started#important-caveat
  // https://www.i18next.com/principles/fallback#key-fallback
  keySeparator: false,
  nsSeparator: false,
});

export default i18n;
