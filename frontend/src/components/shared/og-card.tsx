import React from "react";

/**
 * Satori-compatible OG card (pure object tree — no client code).
 * Shared by the root, /indicators/[id] and /countries/[id] OG images.
 * Palette mirrors the app: warm paper, ink, terracotta.
 */

const INK = "#211d1a";
const PAPER = "#faf8f1";
const TERRACOTTA = "#b85438";
const MUTED = "#8a8078";

export interface OgCardProps {
  title: string;
  subtitle: string;
  badge?: string;
}

export function OgCard({ title, subtitle, badge }: OgCardProps) {
  const displayTitle =
    title.length > 80 ? `${title.slice(0, 79)}…` : title;
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        backgroundColor: PAPER,
        color: INK,
        padding: 72,
        fontFamily: "sans-serif",
      }}
    >
      {/* Wordmark row */}
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <div
          style={{
            width: 56,
            height: 56,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            backgroundColor: TERRACOTTA,
            color: "#faf8f1",
            fontSize: 34,
            fontWeight: 700,
            borderRadius: 14,
          }}
        >
          T
        </div>
        <div style={{ display: "flex", fontSize: 44, fontWeight: 700 }}>
          <span>Todd</span>
          <span style={{ color: TERRACOTTA }}>Lab</span>
        </div>
      </div>

      {/* Title block */}
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {badge && (
          <div
            style={{
              display: "flex",
              alignSelf: "flex-start",
              padding: "8px 18px",
              border: `2px solid ${TERRACOTTA}`,
              color: TERRACOTTA,
              borderRadius: 999,
              fontSize: 22,
              fontWeight: 600,
              letterSpacing: 1,
              textTransform: "uppercase",
            }}
          >
            {badge}
          </div>
        )}
        <div
          style={{
            display: "flex",
            fontSize: displayTitle.length > 40 ? 64 : 84,
            fontWeight: 700,
            lineHeight: 1.1,
            maxWidth: 1000,
          }}
        >
          {displayTitle}
        </div>
      </div>

      {/* Footer */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", height: 4, width: 120, backgroundColor: TERRACOTTA }} />
        <div style={{ display: "flex", fontSize: 28, color: MUTED }}>{subtitle}</div>
      </div>
    </div>
  );
}
