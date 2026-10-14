"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  startTransition,
  useState,
} from "react";
import { en, fr, type Dictionary } from "./dictionaries";
import {
  ENTITY_LABELS_EN,
  ENTITY_LABELS_FR,
  FAMILY_LABELS_FR,
  INDICATOR_LABELS_FR,
  UNIT_LABELS_EN,
  UNIT_LABELS_FR,
} from "./labels-fr";
import {
  INDICATOR_DESCRIPTIONS,
  PROVIDER_LABELS_EN,
  PROVIDER_LABELS_FR,
} from "./descriptions";

import { LANG_COOKIE, type Lang } from "./lang";

export type { Lang };

const ONE_YEAR_S = 60 * 60 * 24 * 365;

function writeLangCookie(l: Lang) {
  document.cookie = `${LANG_COOKIE}=${l}; path=/; max-age=${ONE_YEAR_S}; samesite=lax`;
}

interface I18nContextValue {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (fn: (d: Dictionary) => string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({
  children,
  initialLang,
}: {
  children: React.ReactNode;
  /** Language decided by the server (cookie, then Accept-Language): no flash of English. */
  initialLang: Lang;
}) {
  const [lang, setLangState] = useState<Lang>(initialLang);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    writeLangCookie(l);
  }, []);

  const t = useCallback(
    (fn: (d: Dictionary) => string) => fn(lang === "fr" ? fr : en),
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

/* ------------------------- Content label helpers ------------------------- */

export function useIndicatorLabel(): (id: string, enLabel: string) => string {
  const { lang } = useI18n();
  return useCallback(
    (id: string, enLabel: string) =>
      lang === "fr" ? (INDICATOR_LABELS_FR[id] ?? enLabel) : enLabel,
    [lang],
  );
}

export function useEntityLabel(): (id: string, enLabel?: string) => string {
  const { lang } = useI18n();
  return useCallback(
    (id: string, enLabel?: string) => {
      if (lang === "fr") return ENTITY_LABELS_FR[id] ?? enLabel ?? ENTITY_LABELS_EN[id] ?? id;
      return enLabel ?? ENTITY_LABELS_EN[id] ?? id;
    },
    [lang],
  );
}

export function useFamilyLabel(): (family: string) => string {
  const { lang } = useI18n();
  return useCallback(
    (family: string) => {
      if (lang === "fr") return FAMILY_LABELS_FR[family] ?? family;
      // Capitalize english family as fallback
      return family.charAt(0).toUpperCase() + family.slice(1);
    },
    [lang],
  );
}

export function useUnitLabel(): (unit: string) => string {
  const { lang } = useI18n();
  return useCallback(
    (unit: string) => (lang === "fr" ? (UNIT_LABELS_FR[unit] ?? unit) : (UNIT_LABELS_EN[unit] ?? unit)),
    [lang],
  );
}

/** Short plain-language description of an indicator, in the current language. */
export function useIndicatorDescription(): (id: string) => string | null {
  const { lang } = useI18n();
  return useCallback(
    (id: string) => {
      const d = INDICATOR_DESCRIPTIONS[id];
      if (!d) return null;
      return lang === "fr" ? (d.fr ?? d.en) : d.en;
    },
    [lang],
  );
}

/** Human-readable provider name ("un_dyb" → "UN Demographic Yearbook"). */
export function useProviderLabel(): (provider: string) => string {
  const { lang } = useI18n();
  return useCallback(
    (provider: string) =>
      lang === "fr"
        ? (PROVIDER_LABELS_FR[provider] ?? provider)
        : (PROVIDER_LABELS_EN[provider] ?? provider),
    [lang],
  );
}

/** Simple {placeholder} interpolation for dictionary strings. */
export function interpolate(
  template: string,
  vars: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? `{${k}}`));
}
