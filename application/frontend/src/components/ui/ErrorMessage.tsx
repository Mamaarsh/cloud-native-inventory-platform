import { AlertCircle, RefreshCw } from "lucide-react";
import { getApiErrorMessage } from "@/lib/api-error";

interface ErrorMessageProps {
  error: unknown;
  fallbackMessage?: string;
  onRetry?: () => void;
  title?: string;
}

export function ErrorMessage({
  error,
  fallbackMessage,
  onRetry,
  title = "We hit a problem",
}: ErrorMessageProps) {
  return (
    <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-rose-900" role="alert">
      <div className="flex items-start gap-3">
        <AlertCircle className="mt-0.5 size-5 shrink-0 text-rose-600" aria-hidden="true" />
        <div className="min-w-0">
          <p className="font-semibold">{title}</p>
          <p className="mt-1 text-sm text-rose-700">
            {getApiErrorMessage(error, fallbackMessage)}
          </p>
          {onRetry ? (
            <button type="button" onClick={onRetry} className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-rose-700 hover:text-rose-900">
              <RefreshCw className="size-4" aria-hidden="true" /> Retry
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
