import { useId } from "react";
import type { SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
}

export function Select({ label, error, className = "", id, children, ...props }: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;

  return (
    <label htmlFor={selectId} className="block">
      <span className="mb-2 block text-sm font-semibold text-slate-700">{label}</span>
      <select
        id={selectId}
        aria-invalid={Boolean(error)}
        className={`min-h-11 w-full rounded-xl border bg-white px-3.5 text-sm text-slate-900 transition ${
          error ? "border-rose-400" : "border-slate-300 hover:border-slate-400 focus:border-brand-500"
        } ${className}`}
        {...props}
      >
        {children}
      </select>
      {error ? <span className="mt-1.5 block text-xs text-rose-600">{error}</span> : null}
    </label>
  );
}
