import { Navigate, Outlet } from "react-router-dom";
import { RoleGuard } from "@/auth/RoleGuard";
import type { Role } from "@/types";

interface RoleProtectedRouteProps {
  role: Role | Role[];
}

export function RoleProtectedRoute({ role }: RoleProtectedRouteProps) {
  return (
    <RoleGuard role={role} fallback={<Navigate to="/" replace />}>
      <Outlet />
    </RoleGuard>
  );
}
