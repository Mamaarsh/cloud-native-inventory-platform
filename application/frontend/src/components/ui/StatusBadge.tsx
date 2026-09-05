import { Badge } from "@/components/ui/Badge";
import { titleCase } from "@/lib/format";
import type { OrderStatus, PaymentStatus } from "@/types";

interface StatusBadgeProps {
  status: OrderStatus | PaymentStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const tone = {
    pending: "amber",
    processing: "blue",
    shipped: "violet",
    delivered: "green",
    cancelled: "red",
    succeeded: "green",
    failed: "red",
    refunded: "slate",
  }[status] as "amber" | "blue" | "violet" | "green" | "red" | "slate";

  return <Badge tone={tone}>{titleCase(status)}</Badge>;
}
