import { LogOut, Menu } from "lucide-react";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

interface HeaderProps {
  onOpenMenu: () => void;
}

const titles: Record<string, string> = {
  "/": "Operations overview",
  "/products": "Products",
  "/warehouses": "Warehouses",
  "/inventory": "Inventory",
  "/orders": "Orders",
};

export function Header({ onOpenMenu }: HeaderProps) {
  const { currentUser, logout } = useAuth();
  const location = useLocation();
  const title = location.pathname.startsWith("/orders/") ? "Order details" : (titles[location.pathname] ?? "Inventory platform");
  const displayName = [currentUser?.first_name, currentUser?.last_name].filter(Boolean).join(" ") || currentUser?.username;
  const initials = displayName?.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase() || "U";

  return (
    <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onOpenMenu} className="rounded-xl border border-slate-200 p-2.5 text-slate-600 hover:bg-slate-50 lg:hidden" aria-label="Open menu">
          <Menu className="size-5" />
        </button>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.13em] text-brand-600">Workspace</p>
          <h1 className="mt-0.5 text-lg font-bold tracking-tight text-slate-950 sm:text-xl">{title}</h1>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="hidden text-right sm:block">
          <p className="text-sm font-semibold text-slate-900">{displayName}</p>
          <p className="max-w-48 truncate text-xs text-slate-500">{currentUser?.groups.join(" · ") || "Authenticated user"}</p>
        </div>
        <span className="grid size-10 place-items-center rounded-xl bg-slate-900 text-xs font-bold text-white">{initials}</span>
        <button type="button" onClick={logout} className="rounded-xl p-2.5 text-slate-500 hover:bg-rose-50 hover:text-rose-600" aria-label="Log out" title="Log out">
          <LogOut className="size-5" />
        </button>
      </div>
    </header>
  );
}
