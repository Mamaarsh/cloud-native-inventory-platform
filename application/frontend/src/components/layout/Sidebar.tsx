import { Boxes, ClipboardList, LayoutDashboard, PackageSearch, Warehouse, X } from "lucide-react";
import { NavLink } from "react-router-dom";

interface SidebarProps {
  open: boolean;
  onClose: () => void;
}

const links = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/products", label: "Products", icon: PackageSearch, end: false },
  { to: "/warehouses", label: "Warehouses", icon: Warehouse, end: false },
  { to: "/inventory", label: "Inventory", icon: Boxes, end: false },
  { to: "/orders", label: "Orders", icon: ClipboardList, end: false },
];

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {open ? <button type="button" className="fixed inset-0 z-30 bg-slate-950/45 lg:hidden" onClick={onClose} aria-label="Close navigation" /> : null}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col bg-ink-950 text-white transition-transform duration-300 lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="dashboard-grid flex h-20 items-center justify-between border-b border-white/10 px-6">
          <NavLink to="/" onClick={onClose} className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl bg-brand-500 shadow-lg shadow-brand-500/25">
              <Boxes className="size-5" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-base font-bold tracking-tight">Stockline</span>
              <span className="block text-[11px] font-medium uppercase tracking-[0.2em] text-slate-400">Operations</span>
            </span>
          </NavLink>
          <button type="button" onClick={onClose} className="rounded-lg p-2 text-slate-400 hover:bg-white/10 lg:hidden" aria-label="Close menu">
            <X className="size-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1.5 px-4 py-7" aria-label="Primary navigation">
          <p className="mb-3 px-3 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Workspace</p>
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-semibold transition ${
                isActive ? "bg-brand-500 text-white shadow-lg shadow-brand-500/15" : "text-slate-400 hover:bg-white/7 hover:text-white"
              }`}
            >
              <Icon className="size-[18px]" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="m-4 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-emerald-300">
            <span className="size-2 rounded-full bg-emerald-400 shadow-[0_0_10px_#34d399]" /> API connected
          </div>
          <p className="text-xs leading-5 text-slate-400">Inventory operations are secured by backend-enforced RBAC.</p>
        </div>
      </aside>
    </>
  );
}
