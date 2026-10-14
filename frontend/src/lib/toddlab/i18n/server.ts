import "server-only";
import { cookies, headers } from "next/headers";
import { en, fr, type Dictionary } from "./dictionaries";
import { LANG_COOKIE, type Lang } from "./lang";

/**
 * Language of the current request, decided on the server so the first HTML
 * is already in the right language: the language cookie (set by the FR/EN
 * toggle) wins, then the browser's Accept-Language, then English.
 */
export async function getRequestLang(): Promise<Lang> {
  const stored = (await cookies()).get(LANG_COOKIE)?.value;
  if (stored === "fr" || stored === "en") return stored;
  const accept = (await headers()).get("accept-language") ?? "";
  return accept.trim().toLowerCase().startsWith("fr") ? "fr" : "en";
}

export async function getServerDictionary(): Promise<{ lang: Lang; d: Dictionary }> {
  const lang = await getRequestLang();
  return { lang, d: lang === "fr" ? fr : en };
}
