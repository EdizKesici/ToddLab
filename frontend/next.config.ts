import path from "path";
import type { NextConfig } from "next";

// On Vercel the app is deployed from the frontend/ directory but reads the
// backend payload (<repo>/data/dist) at request time, so the file tracer must
// look at the repository root and bundle that directory with every function.
// Locally the self-contained standalone server is used instead (npm start).
const onVercel = Boolean(process.env.VERCEL);

const nextConfig: NextConfig = {
  ...(onVercel
    ? {
        outputFileTracingRoot: path.join(process.cwd(), ".."),
        outputFileTracingIncludes: { "/**": ["../data/dist/**/*"] },
      }
    : { output: "standalone" }),
  reactStrictMode: false,
};

export default nextConfig;
