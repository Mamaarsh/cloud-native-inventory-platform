interface BackgroundFetchIndicatorProps {
  active: boolean;
  label: string;
}

export function BackgroundFetchIndicator({ active, label }: BackgroundFetchIndicatorProps) {
  return (
    <div className="h-0.5" aria-live="polite" aria-atomic="true">
      {active ? (
        <>
          <span className="block h-full bg-brand-500/60" aria-hidden="true" />
          <span className="sr-only">{label}</span>
        </>
      ) : null}
    </div>
  );
}
