import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site-url";
import { getCatalog, getEntities } from "@/lib/toddlab/store";

// No lastModified: a build-time or request-time date would be a made-up value. Reads the backend payload at request time, so a rebuilt data/dist shows up without a frontend rebuild.
export const dynamic = "force-dynamic";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();

  const staticRoutes: MetadataRoute.Sitemap = [
    "",
    "/compare",
    "/countries",
    "/indicators",
    "/score",
    "/predictions",
    "/methodology",
  ].map((path) => ({
    url: `${base}${path}`,
    changeFrequency: "weekly",
    priority: path === "" ? 1 : 0.8,
  }));

  const indicators: MetadataRoute.Sitemap = getCatalog().map((i) => ({
    url: `${base}/indicators/${i.id}`,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  const countries: MetadataRoute.Sitemap = getEntities().map((e) => ({
    url: `${base}/countries/${e.entity_id}`,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  return [...staticRoutes, ...indicators, ...countries];
}
