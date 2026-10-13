import type { Metadata } from "next";
import { Fraunces, Geist_Mono, Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import { siteUrl } from "@/lib/site-url";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  axes: ["SOFT", "WONK"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl()),
  title: {
    default: "ToddLab",
    template: "%s · ToddLab",
  },
  description:
    "Compare countries on hard social indicators — mortality, health, education, demography — with full provenance, honest gaps and modelled estimates. Built on the method of Emmanuel Todd.",
  keywords: [
    "ToddLab",
    "Emmanuel Todd",
    "demography",
    "mortality",
    "social indicators",
    "data comparison",
  ],
  authors: [{ name: "Ediz Kesici" }],
  openGraph: {
    // No title/description here: pages inherit their own metadata into the
    // OG tags — forcing them at the root would freeze og:title to "ToddLab".
    siteName: "ToddLab",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${fraunces.variable} ${geistMono.variable} font-sans antialiased bg-background text-foreground min-h-screen flex flex-col`}
      >
        <Providers>
          <SiteHeader />
          <main className="flex-1">{children}</main>
          <SiteFooter />
        </Providers>
        <Toaster />
      </body>
    </html>
  );
}
