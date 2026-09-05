import { useEffect, useRef, useState } from "react";
import { Boxes, ClipboardList, LayoutDashboard, PackageSearch, Warehouse, X } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";

const mobileBreakpoint = "(max-width: 63.999rem)";
const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled]):not([type='hidden'])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[contenteditable='true']",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export const MOBILE_SIDEBAR_ID = "mobile-navigation-drawer";

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

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(focusableSelector)).filter(
    (element) => !element.hidden && element.getAttribute("aria-hidden") !== "true",
  );
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(() =>
    typeof window === "undefined" ? false : window.matchMedia(mobileBreakpoint).matches,
  );
  const drawerRef = useRef<HTMLElement>(null);
  const navigationRef = useRef<HTMLElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  const previousLocationKeyRef = useRef(location.key);
  const drawerActive = isMobile && open;

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(mobileBreakpoint);

    function handleBreakpointChange(event: MediaQueryListEvent): void {
      setIsMobile(event.matches);
      if (!event.matches) onCloseRef.current();
    }

    mediaQuery.addEventListener("change", handleBreakpointChange);
    return () => mediaQuery.removeEventListener("change", handleBreakpointChange);
  }, []);

  useEffect(() => {
    if (previousLocationKeyRef.current === location.key) return;
    previousLocationKeyRef.current = location.key;
    if (drawerActive) onCloseRef.current();
  }, [drawerActive, location.key]);

  useEffect(() => {
    if (!drawerActive) return undefined;

    const previouslyFocusedElement =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousBodyOverflow = document.body.style.overflow;
    const focusFrame = window.requestAnimationFrame(() => {
      const drawer = drawerRef.current;
      if (!drawer || drawer.contains(document.activeElement)) return;

      const firstNavigationLink = navigationRef.current?.querySelector<HTMLElement>("a[href]");
      (firstNavigationLink ?? closeButtonRef.current ?? drawer).focus();
    });

    function handleKeyDown(event: KeyboardEvent): void {
      const drawer = drawerRef.current;
      if (!drawer) return;

      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }

      if (event.key !== "Tab") return;

      const focusableElements = getFocusableElements(drawer);
      if (focusableElements.length === 0) {
        event.preventDefault();
        drawer.focus();
        return;
      }

      const firstElement = focusableElements[0]!;
      const lastElement = focusableElements[focusableElements.length - 1]!;
      const activeElement = document.activeElement;
      const activeIndex = focusableElements.indexOf(activeElement as HTMLElement);

      if (activeIndex === -1) {
        event.preventDefault();
        (event.shiftKey ? lastElement : firstElement).focus();
      } else if (event.shiftKey && activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousBodyOverflow;
      if (previouslyFocusedElement?.isConnected) previouslyFocusedElement.focus();
    };
  }, [drawerActive]);

  return (
    <>
      {drawerActive ? (
        <div
          aria-hidden="true"
          className="fixed inset-0 z-30 bg-slate-950/45 lg:hidden"
          onClick={onClose}
        />
      ) : null}
      <aside
        id={MOBILE_SIDEBAR_ID}
        ref={drawerRef}
        role={drawerActive ? "dialog" : undefined}
        aria-modal={drawerActive ? "true" : undefined}
        aria-label={drawerActive ? "Navigation drawer" : undefined}
        aria-hidden={isMobile && !open ? "true" : undefined}
        inert={isMobile && !open}
        tabIndex={drawerActive ? -1 : undefined}
        className={`fixed inset-y-0 left-0 z-40 flex w-72 flex-col border-r border-white/10 bg-ink-950 text-white shadow-2xl shadow-slate-950/20 transition-transform duration-300 motion-reduce:transition-none lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="dashboard-grid flex h-20 items-center justify-between border-b border-white/10 bg-white/[0.02] px-5">
          <NavLink to="/" onClick={onClose} className="flex items-center gap-3">
            <span className="grid size-11 place-items-center rounded-xl bg-brand-600 shadow-lg shadow-brand-950/20 ring-1 ring-inset ring-white/20">
              <Boxes className="size-5" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-base font-bold tracking-tight text-white">Stockline</span>
              <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400">Inventory platform</span>
            </span>
          </NavLink>
          <button ref={closeButtonRef} type="button" onClick={onClose} className="grid size-10 place-items-center rounded-lg text-slate-300 hover:bg-white/10 hover:text-white lg:hidden" aria-label="Close menu">
            <X className="size-5" />
          </button>
        </div>
        <nav ref={navigationRef} className="flex-1 space-y-2 px-3 py-6" aria-label="Primary navigation">
          <p className="mb-4 px-4 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Workspace</p>
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) => `relative flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition-colors motion-reduce:transition-none ${
                isActive
                  ? "bg-white/10 text-white ring-1 ring-inset ring-white/10 before:absolute before:bottom-2.5 before:left-0 before:top-2.5 before:w-1 before:rounded-r-full before:bg-brand-500"
                  : "text-slate-400 hover:bg-white/[0.06] hover:text-white"
              }`}
            >
              <Icon className="size-[18px]" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="m-4 rounded-xl border border-white/10 bg-white/[0.04] p-4">
          <p className="mb-2 text-xs font-semibold text-slate-300">API-backed workspace</p>
          <p className="text-xs leading-5 text-slate-400">Inventory operations are secured by backend-enforced RBAC.</p>
        </div>
      </aside>
    </>
  );
}
