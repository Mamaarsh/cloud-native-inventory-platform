import { Menu } from "lucide-react";
import { useLocation } from "react-router-dom";
import { AccountMenu } from "@/components/account/AccountMenu";
import { MOBILE_SIDEBAR_ID } from "@/components/layout/Sidebar";

interface HeaderProps {
  menuOpen: boolean;
  onToggleMenu: () => void;
}

const titles: Record<string, string> = {
  "/": "Operations overview",
  "/products": "Products",
  "/warehouses": "Warehouses",
  "/inventory": "Inventory",
  "/orders": "Orders",
  "/users": "User management",
  "/account": "My account",
};

export function Header({ menuOpen, onToggleMenu }: HeaderProps) {
  const location = useLocation();
  const title = location.pathname.startsWith("/orders/") ? "Order details" : (titles[location.pathname] ?? "Inventory platform");

  return (
    <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200 bg-white px-4 shadow-[0_1px_3px_rgb(15_23_42/0.04)] sm:px-6 lg:px-8">
      <div className="flex min-w-0 items-center gap-3.5">
        <button
          type="button"
          onClick={onToggleMenu}
          aria-expanded={menuOpen}
          aria-controls={MOBILE_SIDEBAR_ID}
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          className="grid size-10 shrink-0 place-items-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900 motion-reduce:transition-none lg:hidden"
        >
          <Menu className="size-5" />
        </button>
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">Workspace</p>
          <h1 className="mt-1 truncate text-lg font-bold tracking-tight text-slate-950 sm:text-xl">{title}</h1>
        </div>
      </div>
      <AccountMenu />
    </header>
  );
}
