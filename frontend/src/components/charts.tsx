"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { primaryManagerName } from "@/lib/display";
import type { GameweekSummary, RankBand } from "@/lib/api";

const muted = "#8a8276";
const accent = "#1f6b4d";
const gold = "#b68438";

type TooltipPayload = {
  dataKey: string;
  name: string;
  value: number | string;
  color: string;
};

function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string | number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-stone-300 bg-[#fffdf7] px-3 py-2 text-xs shadow-sm">
      <div className="mb-1 font-mono text-stone-500">GW {label}</div>
      {payload.map((item) => (
        <div key={item.dataKey} className="flex min-w-36 items-center justify-between gap-5">
          <span style={{ color: item.color }}>{item.name}</span>
          <span className="mono-num font-semibold text-stone-950">{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export function DistributionChart({
  data,
}: {
  data: Array<{ bucket: number; min_points: number; max_points: number; managers: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#e3ded2" />
        <XAxis
          dataKey="min_points"
          tickLine={false}
          axisLine={false}
          tick={{ fill: muted, fontSize: 11 }}
          interval={6}
        />
        <YAxis hide />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(31,107,77,0.08)" }} />
        <Bar dataKey="managers" name="Managers" fill={accent} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function GameweekPulseChart({ data }: { data: GameweekSummary[] }) {
  const rows = data.map((row) => ({
    event: row.event,
    avg: Number(row.avg_points),
    p90: Number(row.p90_points),
    p10: Number(row.p10_points),
    volatility: Number(row.volatility),
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <AreaChart data={rows} margin={{ top: 14, right: 12, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="avgFill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={0.32} />
            <stop offset="100%" stopColor={accent} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="#e3ded2" />
        <XAxis dataKey="event" tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} width={32} />
        <Tooltip content={<ChartTooltip />} />
        <Area type="monotone" dataKey="avg" name="Average" stroke={accent} fill="url(#avgFill)" strokeWidth={2} />
        <Line type="monotone" dataKey="p90" name="P90" stroke={gold} dot={false} strokeWidth={1.5} />
        <Line type="monotone" dataKey="p10" name="P10" stroke="#9b4f3f" dot={false} strokeWidth={1.5} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function RankBandChart({ data }: { data: RankBand[] }) {
  const rows = data.map((row) => ({
    band: row.band,
    weekly: Number(row.avg_weekly_points),
    bench: Number(row.avg_bench_points),
    value: Number(row.avg_team_value),
  }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#e3ded2" />
        <XAxis dataKey="band" tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} width={32} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(31,107,77,0.08)" }} />
        <Bar dataKey="weekly" name="Weekly points" fill={accent} radius={[4, 4, 0, 0]} />
        <Bar dataKey="bench" name="Bench points" fill={gold} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ManagerJourneyChart({
  data,
}: {
  data: Array<{ event: number; points: number; total_points: number; points_on_bench: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart data={data} margin={{ top: 16, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#e3ded2" />
        <XAxis dataKey="event" tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} width={42} />
        <Tooltip content={<ChartTooltip />} />
        <Line type="monotone" dataKey="total_points" name="Total points" stroke={accent} dot={false} strokeWidth={2.5} />
        <Line type="monotone" dataKey="points" name="GW points" stroke={gold} dot={false} strokeWidth={1.5} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ArchetypeChart({
  data,
}: {
  data: Array<{ archetype: string; managers: number; avg_total: string; avg_volatility: string }>;
}) {
  const rows = data.map((row) => ({
    archetype: row.archetype,
    managers: row.managers,
    total: Number(row.avg_total),
    volatility: Number(row.avg_volatility),
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={rows} layout="vertical" margin={{ top: 8, right: 20, left: 34, bottom: 0 }}>
        <CartesianGrid horizontal={false} stroke="#e3ded2" />
        <XAxis type="number" tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} />
        <YAxis
          type="category"
          dataKey="archetype"
          tickLine={false}
          axisLine={false}
          tick={{ fill: muted, fontSize: 11 }}
          width={104}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(31,107,77,0.08)" }} />
        <Bar dataKey="managers" name="Managers" fill={accent} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function PercentileLadderChart({
  data,
}: {
  data: Array<{ label: string; points: number }>;
}) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 6, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#e3ded2" />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} width={40} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(31,107,77,0.08)" }} />
        <Bar dataKey="points" name="Points" fill={accent} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function RankBandHeatmap({
  data,
}: {
  data: Array<{ band: string; event: number; avg_points: string }>;
}) {
  const bands = ["Top 100", "Top 1K", "Top 1%", "Top 5%", "Top 10%", "Median"];
  const max = Math.max(...data.map((row) => Number(row.avg_points)));
  const min = Math.min(...data.map((row) => Number(row.avg_points)));

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[980px]">
        <div className="grid grid-cols-[5rem_repeat(38,minmax(1.35rem,1fr))] gap-1 text-xs">
          <div />
          {Array.from({ length: 38 }, (_, index) => (
            <div key={index + 1} className="mono-num text-center text-[10px] text-stone-400">
              {index + 1}
            </div>
          ))}
          {bands.map((band) => (
            <div key={band} className="contents">
              <div className="flex items-center text-xs font-semibold text-stone-600">{band}</div>
              {Array.from({ length: 38 }, (_, index) => {
                const event = index + 1;
                const row = data.find((item) => item.band === band && item.event === event);
                const value = row ? Number(row.avg_points) : 0;
                const intensity = max === min ? 0 : (value - min) / (max - min);
                return (
                  <div
                    key={`${band}-${event}`}
                    title={`${band} GW${event}: ${value.toFixed(1)} avg pts`}
                    className="h-7 rounded-sm border border-stone-950/5"
                    style={{
                      backgroundColor: `rgba(31, 107, 77, ${0.08 + intensity * 0.74})`,
                    }}
                  />
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function SupporterClubChart({
  data,
}: {
  data: Array<{ short_name: string; team_name: string; managers: number; avg_total: string; share_pct: string }>;
}) {
  const rows = data
    .filter((row) => row.short_name !== "NONE")
    .slice(0, 20)
    .map((row) => ({
      club: row.short_name,
      name: row.team_name,
      managers: row.managers,
      avgTotal: Number(row.avg_total),
      share: Number(row.share_pct),
    }));

  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={rows} margin={{ top: 8, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="#e3ded2" />
        <XAxis dataKey="club" tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} />
        <YAxis tickLine={false} axisLine={false} tick={{ fill: muted, fontSize: 11 }} width={46} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(31,107,77,0.08)" }} />
        <Bar dataKey="managers" name="Supporters" fill={accent} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ConsistencyScatter({
  data,
}: {
  data: Array<Record<string, string | number>>;
}) {
  const rows = data.map((row) => ({
    name: primaryManagerName(row),
    rank: Number(row.rank),
    volatility: Number(row.volatility),
    avg: Number(row.avg_points),
    bench: Number(row.bench_points),
  }));
  return (
    <ResponsiveContainer width="100%" height={380}>
      <ScatterChart margin={{ top: 16, right: 18, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#e3ded2" />
        <XAxis
          type="number"
          dataKey="volatility"
          name="Volatility"
          tickLine={false}
          axisLine={false}
          tick={{ fill: muted, fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="avg"
          name="Avg points"
          tickLine={false}
          axisLine={false}
          tick={{ fill: muted, fontSize: 11 }}
          width={38}
        />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<ChartTooltip />} />
        <Scatter data={rows} fill={accent} fillOpacity={0.58} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function ValueRankScatter({
  data,
}: {
  data: Array<Record<string, string | number>>;
}) {
  const rows = data.map((row) => ({
    rank: Number(row.rank),
    value: Number(row.avg_team_value),
    ppm: Number(row.points_per_million),
  }));
  return (
    <ResponsiveContainer width="100%" height={380}>
      <ScatterChart margin={{ top: 16, right: 18, left: 0, bottom: 8 }}>
        <CartesianGrid stroke="#e3ded2" />
        <XAxis
          type="number"
          dataKey="value"
          name="Avg team value"
          tickLine={false}
          axisLine={false}
          tick={{ fill: muted, fontSize: 11 }}
        />
        <YAxis
          type="number"
          dataKey="rank"
          name="Final rank"
          reversed
          tickLine={false}
          axisLine={false}
          tick={{ fill: muted, fontSize: 11 }}
          width={54}
        />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<ChartTooltip />} />
        <Scatter data={rows} fill={gold} fillOpacity={0.58} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
