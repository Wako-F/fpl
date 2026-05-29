"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { GIFEncoder, quantize, applyPalette } from "gifenc";
import { primaryManagerName } from "@/lib/display";

const nf = new Intl.NumberFormat("en-US");

type RaceRow = {
  entry: number;
  entry_name: string;
  player_name: string;
  final_rank: number;
  event: number;
  total_points: number;
  points: number;
};

export function AnimatedRankRace({ data }: { data: RaceRow[] }) {
  const [event, setEvent] = useState(1);
  const [playing, setPlaying] = useState(true);
  const [exporting, setExporting] = useState(false);
  const visibleCount = 20;

  const frames = useMemo(() => {
    const safeData = Array.isArray(data) ? data : [];
    const grouped = new Map<number, RaceRow[]>();
    for (const row of safeData) {
      if (!row || typeof row.event !== "number") continue;
      const rows = grouped.get(row.event) ?? [];
      rows.push(row);
      grouped.set(row.event, rows);
    }
    return Array.from({ length: 38 }, (_, index) => {
      const gw = index + 1;
      return (grouped.get(gw) ?? [])
        .slice()
        .sort((a, b) => b.total_points - a.total_points || a.final_rank - b.final_rank)
        .slice(0, visibleCount);
    });
  }, [data]);

  const rows = frames[event - 1] ?? [];
  const maxPoints = Math.max(...rows.map((row) => Number(row.total_points) || 0), 1);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setEvent((current) => (current >= 38 ? 1 : current + 1));
    }, 1400);
    return () => window.clearInterval(id);
  }, [playing]);

  async function downloadGif() {
    setExporting(true);
    try {
      const width = 1080;
      const height = 760;
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const encoder = GIFEncoder();
      const frameEvents = Array.from({ length: 38 }, (_, index) => index + 1);

      for (const gw of frameEvents) {
        const frameRows = frames[gw - 1] ?? [];
        const max = Math.max(...frameRows.map((row) => Number(row.total_points) || 0), 1);

        ctx.fillStyle = "#f7f6f0";
        ctx.fillRect(0, 0, width, height);

        ctx.fillStyle = "#1f1d18";
        ctx.font = "700 42px Arial";
        ctx.fillText("FPL Kenya Rank Race", 48, 66);

        ctx.fillStyle = "#1f6b4d";
        ctx.font = "700 30px Arial";
        ctx.fillText(`GW${gw}`, 48, 112);

        ctx.fillStyle = "#706b61";
        ctx.font = "16px Arial";
        ctx.fillText("Top 20 by cumulative points among final top 50 Kenyan managers", 132, 108);

        frameRows.forEach((row, index) => {
          const y = 144 + index * 28;
          const total = Number(row.total_points) || 0;
          const barWidth = Math.max(34, (total / max) * 680);

          ctx.fillStyle = "#e7e0d3";
          roundRect(ctx, 112, y, 720, 20, 6);
          ctx.fill();

          ctx.fillStyle = index < 10 ? "#1f6b4d" : "#587768";
          roundRect(ctx, 112, y, barWidth, 20, 6);
          ctx.fill();

          ctx.fillStyle = "#706b61";
          ctx.font = "700 13px Arial";
          ctx.textAlign = "right";
          ctx.fillText(`#${index + 1}`, 92, y + 15);

          ctx.textAlign = "left";
          ctx.fillStyle = "#fffdf7";
          ctx.font = "700 13px Arial";
          ctx.fillText(truncate(ctx, primaryManagerName(row), 460), 124, y + 15);

          ctx.textAlign = "right";
          ctx.fillStyle = "#1f1d18";
          ctx.font = "700 13px Arial";
          ctx.fillText(nf.format(total), 1010, y + 15);
        });

        ctx.textAlign = "left";
        ctx.fillStyle = "#706b61";
        ctx.font = "13px Arial";
        ctx.fillText("fantasy.premierleague.com data, Kenya country league", 48, 718);

        const imageData = ctx.getImageData(0, 0, width, height);
        const palette = quantize(imageData.data, 256);
        const index = applyPalette(imageData.data, palette);
        encoder.writeFrame(index, width, height, { palette, delay: 320 });
      }

      encoder.finish();
      const bytes = encoder.bytesView();
      const blob = new Blob([new Uint8Array(bytes)], { type: "image/gif" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "fpl-kenya-rank-race.gif";
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-5 border-b border-stone-950/10 pb-6 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mono-num text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">Animated rank race</div>
          <div className="mt-3 flex flex-wrap items-end gap-4">
            <span className="mono-num text-6xl font-semibold leading-none tracking-tight">GW{event}</span>
            <span className="max-w-sm pb-1 text-sm leading-6 text-stone-500">
              Top 20 by cumulative points at this moment in the season.
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setPlaying((value) => !value)}
            className="inline-flex h-10 min-w-10 items-center justify-center rounded-md bg-stone-950 px-3 text-[#fffdf7] transition active:translate-y-px"
            aria-label={playing ? "Pause race" : "Play race"}
          >
            <span className="mono-num text-xs font-semibold">{playing ? "II" : ">"}</span>
          </button>
          <button
            type="button"
            onClick={downloadGif}
            disabled={exporting}
            className="inline-flex h-10 items-center justify-center rounded-md border border-stone-950/10 bg-[#fffdf7] px-4 text-sm font-semibold text-stone-950 transition hover:bg-white active:translate-y-px disabled:cursor-wait disabled:opacity-60"
          >
            {exporting ? "Rendering GIF" : "Download GIF"}
          </button>
          <label className="flex min-w-52 items-center gap-3">
            <span className="mono-num text-xs text-stone-500">1</span>
            <input
              type="range"
              min={1}
              max={38}
              value={event}
              onChange={(changeEvent) => {
                setEvent(Number(changeEvent.target.value));
                setPlaying(false);
              }}
              className="w-full accent-[#1f6b4d]"
            />
            <span className="mono-num text-xs text-stone-500">38</span>
          </label>
        </div>
      </div>

      <div className="relative h-[620px] overflow-hidden rounded-lg bg-[#f2eee4] p-4">
        {rows.map((row, index) => {
          const totalPoints = Number(row.total_points) || 0;
          const width = Math.max(12, (totalPoints / maxPoints) * 100);
          return (
            <Link
              href={`/managers/${row.entry}`}
              key={row.entry}
              className="absolute left-4 right-4 grid grid-cols-[2.75rem_1fr_5.75rem] items-center gap-3 transition-all duration-700 ease-out"
              style={{ transform: `translateY(${14 + index * 29}px)` }}
            >
              <span className="mono-num text-right text-xs font-semibold text-stone-500">{index + 1}</span>
              <span className="relative h-6 overflow-hidden rounded-sm bg-stone-950/[0.055] shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
                <span
                  className="absolute inset-y-0 left-0 rounded-sm bg-[#1f6b4d] transition-[width] duration-700 ease-out"
                  style={{ width: `${width}%` }}
                />
                <span className="absolute inset-0 flex items-center justify-between gap-3 px-2">
                  <span className="min-w-0 truncate text-xs font-semibold leading-6 text-[#fffdf7] mix-blend-difference">
                    {primaryManagerName(row)}
                  </span>
                  <span className="hidden text-[11px] leading-6 text-[#fffdf7] mix-blend-difference md:inline">
                    final #{row.final_rank}
                  </span>
                </span>
              </span>
              <span className="mono-num text-right text-xs font-semibold">{nf.format(totalPoints)}</span>
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
}

function truncate(ctx: CanvasRenderingContext2D, text: string, maxWidth: number) {
  if (ctx.measureText(text).width <= maxWidth) return text;
  let output = text;
  while (output.length > 3 && ctx.measureText(`${output}...`).width > maxWidth) {
    output = output.slice(0, -1);
  }
  return `${output}...`;
}
