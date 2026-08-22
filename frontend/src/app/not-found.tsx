import Link from "next/link";
import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import { SiteHeader } from "@/components/shell";

export default function NotFound() {
  return <><SiteHeader /><main id="main-content" className="mx-auto grid min-h-[70dvh] max-w-[1500px] content-center px-5 py-16 md:px-8"><div className="font-mono text-xs uppercase tracking-[0.22em] text-[#1f6b4d]">404 · offside</div><h1 className="mt-5 max-w-4xl text-5xl font-semibold leading-[0.95] tracking-[-0.05em] md:text-8xl">That page is outside the captured squad.</h1><p className="mt-6 max-w-xl leading-7 text-stone-600">The manager may not be part of the latest deep cohort, or the page may have moved.</p><Link href="/" className="mt-8 inline-flex items-center gap-2 text-sm font-semibold text-[#1f6b4d]"><ArrowLeft size={16} /> Return to this gameweek</Link></main></>;
}
