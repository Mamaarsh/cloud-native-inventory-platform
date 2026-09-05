import { LoaderCircle } from "lucide-react";

interface SpinnerProps {
  label?: string;
  compact?: boolean;
}

export function Spinner({ label = "Loading", compact = false }: SpinnerProps) {
  return (
    <div
      className={`flex items-center gap-3 font-medium text-slate-500 ${compact ? "min-h-9 justify-start text-xs" : "justify-center py-10 text-sm"}`}
      role="status"
    >
      <LoaderCircle className={`${compact ? "size-4" : "size-5"} animate-spin text-brand-600`} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
