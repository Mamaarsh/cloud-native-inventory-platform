import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Input } from "@/components/ui/Input";
import type { InventoryAdjustmentRequest } from "@/types";

interface InventoryAdjustmentFormProps {
  currentQuantity: number;
  onSubmit: (payload: InventoryAdjustmentRequest) => Promise<void>;
  onCancel: () => void;
  isSubmitting: boolean;
  serverError?: unknown;
}

interface AdjustmentErrors {
  quantityDelta?: string;
  reason?: string;
}

export function InventoryAdjustmentForm({
  currentQuantity,
  onSubmit,
  onCancel,
  isSubmitting,
  serverError,
}: InventoryAdjustmentFormProps) {
  const [quantityDelta, setQuantityDelta] = useState("");
  const [reason, setReason] = useState("");
  const [errors, setErrors] = useState<AdjustmentErrors>({});
  const parsedDelta = quantityDelta.trim() === ""
    ? null
    : Number(quantityDelta);
  const hasValidIntegerDelta = parsedDelta !== null
    && Number.isInteger(parsedDelta)
    && parsedDelta !== 0;
  const expectedQuantity = hasValidIntegerDelta
    ? currentQuantity + parsedDelta
    : null;

  async function handleSubmit(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    const nextErrors: AdjustmentErrors = {};

    if (!hasValidIntegerDelta) {
      nextErrors.quantityDelta = "Enter a positive or negative whole number other than zero.";
    } else if (expectedQuantity !== null && expectedQuantity < 0) {
      nextErrors.quantityDelta = "This adjustment would make inventory negative.";
    }
    if (!reason.trim()) {
      nextErrors.reason = "Explain why this stock adjustment is required.";
    }

    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0 || parsedDelta === null) return;

    try {
      await onSubmit({
        quantity_delta: parsedDelta,
        reason: reason.trim(),
      });
    } catch {
      // TanStack Query exposes the backend error through mutation state.
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
      {serverError ? (
        <ErrorMessage
          error={serverError}
          title="Stock could not be adjusted"
        />
      ) : null}

      <div className="grid grid-cols-2 gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <div>
          <p className="text-xs font-semibold text-slate-500">Current quantity</p>
          <p className="mt-1 text-2xl font-bold tabular-nums text-slate-950">
            {currentQuantity.toLocaleString()}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-500">Expected quantity</p>
          <p
            className={`mt-1 text-2xl font-bold tabular-nums ${
              expectedQuantity !== null && expectedQuantity < 0
                ? "text-rose-700"
                : "text-slate-950"
            }`}
          >
            {expectedQuantity === null
              ? "—"
              : expectedQuantity.toLocaleString()}
          </p>
        </div>
      </div>

      <Input
        label="Adjustment"
        type="number"
        step="1"
        value={quantityDelta}
        onChange={(event) => {
          setQuantityDelta(event.target.value);
          setErrors((current) => ({ ...current, quantityDelta: undefined }));
        }}
        error={errors.quantityDelta}
        hint="Use a positive number to add stock or a negative number to remove it."
        placeholder="e.g. 10 or -3"
        disabled={isSubmitting}
        autoFocus
        required
      />

      <Input
        label="Reason"
        dir="auto"
        value={reason}
        onChange={(event) => {
          setReason(event.target.value);
          setErrors((current) => ({ ...current, reason: undefined }));
        }}
        error={errors.reason}
        hint="This explanation becomes part of the permanent movement history."
        maxLength={255}
        disabled={isSubmitting}
        required
      />

      <div className="flex justify-end gap-3 border-t border-slate-200 pt-5">
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
        <Button type="submit" isLoading={isSubmitting}>
          Adjust stock
        </Button>
      </div>
    </form>
  );
}
