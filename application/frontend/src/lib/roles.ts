import { ROLES } from "@/types";
import type { Role } from "@/types";

export const APPLICATION_ROLES: readonly Role[] = Object.values(ROLES);

export function getApplicationRoles(groups: string[]): Role[] {
  return APPLICATION_ROLES.filter((role) => groups.includes(role));
}
