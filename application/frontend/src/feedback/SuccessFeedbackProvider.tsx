import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { CheckCircle2 } from "lucide-react";
import { SuccessFeedbackContext } from "@/feedback/SuccessFeedbackContext";

interface SuccessFeedbackProviderProps {
  children: ReactNode;
}

const dismissDelay = 4_000;

export function SuccessFeedbackProvider({ children }: SuccessFeedbackProviderProps) {
  const [message, setMessage] = useState<string | null>(null);
  const timeoutRef = useRef<number | null>(null);

  const showSuccess = useCallback((nextMessage: string) => {
    if (timeoutRef.current !== null) window.clearTimeout(timeoutRef.current);
    setMessage(nextMessage);
    timeoutRef.current = window.setTimeout(() => {
      setMessage(null);
      timeoutRef.current = null;
    }, dismissDelay);
  }, []);

  useEffect(
    () => () => {
      if (timeoutRef.current !== null) window.clearTimeout(timeoutRef.current);
    },
    [],
  );

  const value = useMemo(() => ({ showSuccess }), [showSuccess]);

  return (
    <SuccessFeedbackContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed inset-x-4 top-4 z-[70] flex justify-end"
        aria-live="polite"
        aria-atomic="true"
      >
        {message ? (
          <div className="flex max-w-sm items-center gap-2 rounded-xl border border-emerald-200 bg-white px-4 py-3 text-sm font-medium text-emerald-800 shadow-soft">
            <CheckCircle2 className="size-4 shrink-0 text-emerald-600" aria-hidden="true" />
            {message}
          </div>
        ) : null}
      </div>
    </SuccessFeedbackContext.Provider>
  );
}
