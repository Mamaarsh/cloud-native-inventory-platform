import type { ReactNode } from "react";
import { Boxes, LockKeyhole, ShieldCheck } from "lucide-react";

interface AuthLayoutProps {
  children: ReactNode;
  contentWidth?: "md" | "lg";
}

const contentWidths = {
  md: "max-w-md",
  lg: "max-w-xl",
} as const;

export function AuthLayout({ children, contentWidth = "md" }: AuthLayoutProps) {
  return (
    <main className="grid min-h-screen bg-ink-950 lg:grid-cols-[1.05fr_0.95fr]">
      <section className="dashboard-grid relative hidden overflow-hidden border-r border-white/10 p-12 lg:flex lg:flex-col lg:justify-between xl:p-16">
        <div className="relative flex items-center gap-3 text-white">
          <span className="grid size-11 place-items-center rounded-xl bg-brand-600 shadow-lg shadow-black/20 ring-1 ring-inset ring-white/20">
            <Boxes className="size-6" aria-hidden="true" />
          </span>
          <div>
            <p className="text-lg font-bold">Stockline</p>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Inventory operations</p>
          </div>
        </div>
        <div className="relative max-w-xl">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-brand-500">Operations workspace</p>
          <h1 className="mt-5 text-4xl font-bold leading-[1.12] tracking-[-0.035em] text-white xl:text-5xl">
            Secure access to inventory operations.
          </h1>
          <p className="mt-6 max-w-lg text-base leading-7 text-slate-400">
            Manage stock, warehouse records, and order fulfillment from one focused workspace.
          </p>
          <div className="mt-10 grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <ShieldCheck className="size-5 text-emerald-400" aria-hidden="true" />
              <p className="mt-4 text-sm font-semibold text-white">Role-aware access</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">Actions match backend-enforced permissions.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
              <LockKeyhole className="size-5 text-brand-500" aria-hidden="true" />
              <p className="mt-4 text-sm font-semibold text-white">Secure sessions</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">JWT access with automatic refresh.</p>
            </div>
          </div>
        </div>
        <p className="relative text-xs font-medium text-slate-500">Cloud Native Inventory Platform</p>
      </section>
      <section className="flex items-center justify-center bg-slate-100/80 px-5 py-12 sm:px-10">
        <div className={`w-full ${contentWidths[contentWidth]} rounded-2xl border border-slate-200 bg-white p-7 shadow-[0_2px_4px_rgb(15_23_42/0.04),0_20px_55px_rgb(15_23_42/0.08)] sm:p-9`}>
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="grid size-10 place-items-center rounded-xl bg-brand-600 text-white shadow-sm">
              <Boxes className="size-5" aria-hidden="true" />
            </span>
            <span className="font-bold text-slate-950">Stockline</span>
          </div>
          {children}
        </div>
      </section>
    </main>
  );
}
