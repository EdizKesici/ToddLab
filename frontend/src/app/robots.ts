import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site-url";

export default function robots(): MetadataRoute.Robots {
  return {
    // /api/ is NOT disallowed: the pages fetch their data from it in the browser,
    // and a crawler that may not read it renders them empty. The API answers
    // with `X-Robots-Tag: noindex` instead (next.config.ts), so it is read for
    // rendering but never listed in search results.
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${siteUrl()}/sitemap.xml`,
  };
}
