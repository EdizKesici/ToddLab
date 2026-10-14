/**
 * Canonical site URL, shared by metadata (metadataBase), sitemap and robots.
 * Priority: explicit NEXT_PUBLIC_SITE_URL → Vercel production domain → Vercel
 * deployment URL → localhost.
 */
export function siteUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_SITE_URL;
  if (explicit) return explicit.replace(/\/$/, "");
  const vercelProd = process.env.VERCEL_PROJECT_PRODUCTION_URL;
  if (vercelProd) return `https://${vercelProd}`;
  const vercel = process.env.VERCEL_URL;
  if (vercel) return `https://${vercel}`;
  return "http://localhost:3000";
}
