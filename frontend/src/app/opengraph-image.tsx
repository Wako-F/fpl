import { ImageResponse } from "next/og";

export const alt = "FPL Kenya — Gameweek data through a Kenyan lens";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(<div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "#f7f6f0", color: "#1f1d18", padding: "64px", fontFamily: "sans-serif" }}><div style={{ display: "flex", alignItems: "center", gap: "18px", fontSize: 24, fontWeight: 700 }}><div style={{ display: "flex", width: 52, height: 52, alignItems: "center", justifyContent: "center", borderRadius: 8, background: "#1f1d18", color: "#f7f6f0" }}>FK</div>FPL Kenya · 2026/27</div><div style={{ display: "flex", flexDirection: "column" }}><div style={{ color: "#1f6b4d", fontSize: 22, letterSpacing: "0.18em", textTransform: "uppercase" }}>The Kenyan FPL data desk</div><div style={{ display: "flex", maxWidth: 1000, marginTop: 20, fontSize: 76, fontWeight: 700, lineHeight: 0.96, letterSpacing: "-0.045em" }}>Every gameweek, through a Kenyan lens.</div></div></div>, size);
}
