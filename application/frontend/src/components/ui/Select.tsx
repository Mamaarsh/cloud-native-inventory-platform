import { useId } from "react";
import type { SelectHTMLAttributes } from "react";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
}

export function Select({ label, error, className = "", id, children, ...props }: SelectProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  const errorId = `${selectId}-error`;

  return (
    <label htmlFor={selectId} className="block">
      <span className="mb-2 block text-[13px] font-bold text-slate-700">{label}</span>
      <select
        id={selectId}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className={`min-h-11 w-full rounded-xl border bg-white px-3.5 text-sm text-slate-900 shadow-sm transition-colors motion-reduce:transition-none disabled:cursor-not-allowed disabled:bg-slate-100 disabled:shadow-none ${
          error ? "border-rose-400" : "border-slate-300 hover:border-slate-400 focus:border-brand-600"
        } ${className}`}
        {...props}
      >
        {children}
      </select>
      {error ? <span id={errorId} className="mt-1.5 block text-xs text-rose-600">{error}</span> : null}
    </label>
  );
}
