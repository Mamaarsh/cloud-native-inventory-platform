import { useId } from "react";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function Input({ label, error, hint, className = "", id, ...props }: InputProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const descriptionId = `${inputId}-description`;

  return (
    <label htmlFor={inputId} className="block">
      <span className="mb-2 block text-[13px] font-bold text-slate-700">{label}</span>
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={error || hint ? descriptionId : undefined}
        className={`min-h-11 w-full rounded-xl border bg-white px-3.5 text-sm text-slate-900 shadow-sm transition-colors motion-reduce:transition-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:shadow-none ${
          error
            ? "border-rose-400 focus:border-rose-500"
            : "border-slate-300 hover:border-slate-400 focus:border-brand-600"
        } ${className}`}
        {...props}
      />
      {error || hint ? (
        <span id={descriptionId} className={`mt-1.5 block text-xs ${error ? "text-rose-600" : "text-slate-500"}`}>
          {error ?? hint}
        </span>
      ) : null}
    </label>
  );
}
