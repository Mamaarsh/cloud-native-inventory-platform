import { ArrowLeft, SearchX } from "lucide-react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/Card";

export function NotFoundPage() {
  return (
    <div className="grid min-h-[65vh] place-items-center">
      <Card className="max-w-lg p-10 text-center">
        <span className="mx-auto grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-500"><SearchX className="size-6" /></span>
        <p className="mt-5 text-xs font-bold uppercase tracking-[0.2em] text-brand-600">404</p>
        <h2 className="mt-2 text-2xl font-bold text-slate-950">Page not found</h2>
        <p className="mt-3 text-sm leading-6 text-slate-500">The page may have moved, or the address may be incorrect.</p>
        <Link to="/" className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-brand-700 hover:text-brand-500"><ArrowLeft className="size-4" /> Return to dashboard</Link>
      </Card>
    </div>
  );
}
