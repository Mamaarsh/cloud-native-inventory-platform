import { Badge } from "@/components/ui/Badge";
import { titleCase } from "@/lib/format";
import type { OrderStatus, PaymentStatus } from "@/types";

interface StatusBadgeProps {
  status: OrderStatus | PaymentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const styles = {
    pending: { tone: "amber", dot: "bg-amber-500" },
    processing: { tone: "blue", dot: "bg-blue-500" },
    shipped: { tone: "violet", dot: "bg-violet-500" },
    delivered: { tone: "green", dot: "bg-emerald-500" },
    cancelled: { tone: "red", dot: "bg-rose-500" },
    succeeded: { tone: "green", dot: "bg-emerald-500" },
    failed: { tone: "red", dot: "bg-rose-500" },
    refunded: { tone: "slate", dot: "bg-slate-500" },
  }[status] as {
    tone: "amber" | "blue" | "violet" | "green" | "red" | "slate";
    dot: string;
  };

  return (
    <Badge tone={styles.tone}>
      <span className={`size-1.5 rounded-full ${styles.dot}`} aria-hidden="true" />
      {titleCase(status)}
    </Badge>
  );
}
