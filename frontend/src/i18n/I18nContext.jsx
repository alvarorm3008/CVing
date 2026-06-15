import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getNested, translations, UI_LANGUAGES } from "./translations.js";

const STORAGE_KEY = "cv-adapter-ui-language";

const I18nContext = createContext({
  locale: "es",
  setLocale: () => {},
  t: (key) => key,
  uiLanguages: UI_LANGUAGES,
});

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) || "es";
    } catch {
      return "es";
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, locale);
    } catch {
      /* ignore */
    }
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((code) => {
    setLocaleState(code);
  }, []);

  const t = useCallback(
    (key, fallback = key) => {
      const pack = translations[locale] || translations.es;
      const value = getNested(pack, key);
      if (value !== undefined && value !== null) return value;
      const esValue = getNested(translations.es, key);
      return esValue ?? fallback;
    },
    [locale],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, uiLanguages: UI_LANGUAGES }),
    [locale, setLocale, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
