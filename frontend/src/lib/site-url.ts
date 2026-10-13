/**
 * Canonical site URL, shared by metadata (metadataBase), sitemap and robots.
 * Priority: explicit NEXT_PUBLIC_SITE_URL → Vercel deployment URL → localhost.
 */
export function siteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL;
  if (explicit) return explicit.replace(/\/$/, "");
  const vercel = process.env.VERCEL_URL;
  if (vercel) return `https://${vercel}`;
  return "http://localhost:3000";
}
