import { useEffect, useRef, useState } from "react";
import { ChevronDown, LogOut, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { ROLES } from "@/types";

export function AccountMenu() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const { currentUser, hasRole, logout } = useAuth();

  const displayName = [currentUser?.first_name, currentUser?.last_name]
    .filter(Boolean)
    .join(" ") || currentUser?.username;
  const initials = displayName
    ?.split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() || "U";
  const primaryRole = Object.values(ROLES).find((role) => hasRole(role))
    ?? currentUser?.groups[0]
    ?? "Authenticated user";

  useEffect(() => {
    if (!open) return undefined;

    function handlePointerDown(event: PointerEvent): void {
      if (event.target instanceof Node && !containerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function handleLogout(): void {
    setOpen(false);
    logout();
  }

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-controls="account-menu"
        aria-label={open ? "Close account options" : "Open account options"}
        className={`flex items-center gap-2 rounded-xl border p-1.5 transition-colors motion-reduce:transition-none ${
          open
            ? "border-slate-200 bg-slate-50 shadow-sm"
            : "border-transparent hover:border-slate-200 hover:bg-slate-50"
        }`}
      >
        <div className="hidden max-w-48 text-right sm:block">
          <p dir="auto" className="truncate text-sm font-semibold text-slate-900">
            {currentUser?.username}
          </p>
          <p className="truncate text-xs text-slate-500">{primaryRole}</p>
        </div>
        <span className="grid size-10 place-items-center rounded-xl bg-brand-600 text-xs font-bold text-white shadow-sm ring-4 ring-brand-50">
          {initials}
        </span>
        <ChevronDown
          className={`size-4 text-slate-400 transition-transform duration-150 motion-reduce:transition-none ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      {open ? (
        <div
          id="account-menu"
          className="absolute right-0 top-[calc(100%+0.65rem)] w-72 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-[0_18px_48px_rgb(15_23_42/0.14)]"
        >
          <div className="border-b border-slate-200 bg-slate-50/70 px-4 py-4">
            <div className="flex items-center gap-3">
              <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-xs font-bold text-brand-700">
                {initials}
              </span>
              <div className="min-w-0">
                <p dir="auto" className="truncate text-sm font-bold text-slate-900">
                  {displayName}
                </p>
                <p dir="auto" className="mt-0.5 truncate text-xs text-slate-500">
                  @{currentUser?.username}
                </p>
                <p className="mt-0.5 truncate text-xs text-slate-500">{primaryRole}</p>
              </div>
            </div>
          </div>
          <div className="p-2">
            <Link
              to="/account"
              onClick={() => setOpen(false)}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50 hover:text-slate-950"
            >
              <UserRound className="size-4 text-slate-400" aria-hidden="true" />
              My Account
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-rose-600 transition-colors hover:bg-rose-50"
            >
              <LogOut className="size-4" aria-hidden="true" />
              Logout
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
