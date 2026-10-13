import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site-url";
import { getCatalog, getEntities } from "@/lib/toddlab/store";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteUrl();
  const now = new Date();

  const staticRoutes: MetadataRoute.Sitemap = [
    "",
    "/compare",
    "/countries",
    "/indicators",
    "/score",
    "/methodology",
  ].map((path) => ({
    url: `${base}${path}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: path === "" ? 1 : 0.8,
  }));

  const indicators: MetadataRoute.Sitemap = getCatalog().map((i) => ({
    url: `${base}/indicators/${i.id}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  const countries: MetadataRoute.Sitemap = getEntities().map((e) => ({
    url: `${base}/countries/${e.entity_id}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  return [...staticRoutes, ...indicators, ...countries];
}
