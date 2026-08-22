"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="grid min-h-dvh place-items-center bg-[#f7f6f0] px-5"><div className="max-w-xl"><div className="font-mono text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">Data connection interrupted</div><h1 className="mt-5 text-5xl font-semibold tracking-[-0.05em]">The latest numbers did not arrive.</h1><p className="mt-5 leading-7 text-stone-600">The data API may be refreshing. Try the request again; no published result has been changed.</p><button type="button" onClick={reset} className="mt-7 rounded-md bg-stone-950 px-4 py-3 text-sm font-semibold text-[#fffdf7] transition active:translate-y-px">Try again</button></div></main>;
}
