import { LoaderCircle } from "lucide-react";

interface SpinnerProps {
  label?: string;
}

export function Spinner({ label = "Loading" }: SpinnerProps) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-sm font-medium text-slate-500" role="status">
      <LoaderCircle className="size-5 animate-spin text-brand-600" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
