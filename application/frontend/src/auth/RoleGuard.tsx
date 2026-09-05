import type { ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";
import type { Role } from "@/types";

interface RoleGuardProps {
  role: Role | Role[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function RoleGuard({ role, children, fallback = null }: RoleGuardProps) {
  const { hasRole } = useAuth();
  return hasRole(role) ? children : fallback;
}

export const RequireRole = RoleGuard;
