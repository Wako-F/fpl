"use client";

import Link from "next/link";
import { MagnifyingGlass, SpinnerGap } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import type { LeaderboardRow } from "@/lib/api";
import { primaryManagerName, secondaryManagerName } from "@/lib/display";

const nf = new Intl.NumberFormat("en-US");
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function LeaderboardSearch({ initialRows, event }: { initialRows: LeaderboardRow[]; event: number }) {
  const [query, setQuery] = useState("");
  const [rows, setRows] = useState(initialRows);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const handle = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams({ limit: "100" });
        if (query.trim()) params.set("q", query.trim());
        const response = await fetch(`${basePath}/api/leaderboard?${params}`, { signal: controller.signal });
        if (!response.ok) throw new Error("Search failed");
        setRows(await response.json());
      } catch {
        if (!controller.signal.aborted) setError("Could not load leaderboard results.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 240);
    return () => {
      controller.abort();
      window.clearTimeout(handle);
    };
  }, [query]);

  const subtitle = useMemo(() => {
    if (query.trim()) return `${rows.length} matching managers`;
    return "Top 100 managers in Kenya";
  }, [query, rows.length]);

  return (
    <div className="panel rounded-lg">
      <div className="flex flex-col gap-4 border-b border-stone-950/10 p-5 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="text-xl font-semibold tracking-tight">Leaderboard explorer</div>
          <div className="mt-1 text-sm text-stone-500">{subtitle}</div>
        </div>
        <label className="block w-full max-w-md">
          <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">
            Search manager or team
          </span>
          <span className="flex items-center gap-2 rounded-md border border-stone-950/10 bg-[#fffdf7] px-3 py-2">
            <MagnifyingGlass size={18} className="text-stone-500" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="h-9 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-stone-400"
              placeholder="Try Joseph Kago or an entry ID"
            />
            {loading ? <SpinnerGap size={16} className="animate-spin text-[#1f6b4d]" /> : null}
          </span>
          {error ? <span className="mt-2 block text-xs text-red-700">{error}</span> : null}
        </label>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="border-b border-stone-950/10 text-xs uppercase tracking-[0.16em] text-stone-500">
            <tr>
              <th className="px-5 py-3 font-semibold">Rank</th>
              <th className="px-5 py-3 font-semibold">Team</th>
              <th className="px-5 py-3 font-semibold">Manager</th>
              <th className="px-5 py-3 text-right font-semibold">Total</th>
              <th className="px-5 py-3 text-right font-semibold">GW{event}</th>
              <th className="px-5 py-3 text-right font-semibold">Move</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-950/10">
            {rows.map((row) => {
              const movement = row.last_rank - row.rank;
              return (
                <tr key={row.entry} className="transition hover:bg-stone-950/[0.025]">
                  <td className="mono-num px-5 py-4 text-stone-500">#{nf.format(row.rank)}</td>
                  <td className="px-5 py-4">
                    <Link href={`/managers/${row.entry}`} className="font-semibold text-stone-950 hover:text-[#1f6b4d]">
                      {primaryManagerName(row)}
                    </Link>
                  </td>
                  <td className="px-5 py-4 text-stone-600">{secondaryManagerName(row)}</td>
                  <td className="mono-num px-5 py-4 text-right font-semibold">{nf.format(row.total)}</td>
                  <td className="mono-num px-5 py-4 text-right">{row.event_total}</td>
                  <td className="mono-num px-5 py-4 text-right">
                    {movement > 0 ? `+${nf.format(movement)}` : nf.format(movement)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
