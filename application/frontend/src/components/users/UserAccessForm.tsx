import { useState } from "react";
import type { FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Select } from "@/components/ui/Select";
import { getApiFieldErrors } from "@/lib/api-error";
import { APPLICATION_ROLES, getApplicationRoles } from "@/lib/roles";
import type { AdminUser, Role } from "@/types";

interface UserAccessFormProps {
  user: AdminUser;
  isSubmitting: boolean;
  serverError: unknown;
  onSubmit: (role: Role) => Promise<void>;
  onCancel: () => void;
  onResetError: () => void;
}

const roleErrorFields = ["role"] as const;

export function UserAccessForm({
  user,
  isSubmitting,
  serverError,
  onSubmit,
  onCancel,
  onResetError,
}: UserAccessFormProps) {
  const currentRoles = getApplicationRoles(user.groups);
  const [role, setRole] = useState<Role | "">(currentRoles[0] ?? "");
  const [clientError, setClientError] = useState<string>();
  const backendRoleError = getApiFieldErrors(serverError, roleErrorFields).role;

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!role) {
      setClientError("Select an application role.");
      return;
    }
    await onSubmit(role);
  }

  const displayName = [user.first_name, user.last_name]
    .filter(Boolean)
    .join(" ");

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="space-y-5">
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <p dir="auto" className="font-bold text-slate-950">{displayName || user.username}</p>
        <p className="mt-1 text-sm text-slate-600">@{user.username}</p>
        {user.email ? <p className="mt-1 break-all text-xs text-slate-500">{user.email}</p> : null}
      </div>

      {serverError && !backendRoleError ? <ErrorMessage error={serverError} title="Access update failed" /> : null}

      <Select
        label="Application role"
        value={role}
        error={clientError ?? backendRoleError}
        disabled={isSubmitting}
        data-modal-initial-focus="true"
        onChange={(event) => {
          setRole(event.target.value as Role | "");
          setClientError(undefined);
          onResetError();
        }}
      >
        <option value="">Select a role</option>
        {APPLICATION_ROLES.map((roleName) => (
          <option key={roleName} value={roleName}>{roleName}</option>
        ))}
      </Select>

      <p className="text-xs leading-5 text-slate-500">
        {user.is_active
          ? "Saving replaces the current application role. Staff status and permissions are not changed."
          : "Approval activates the account and assigns the selected application role in one update."}
      </p>

      <div className="flex flex-col-reverse gap-3 border-t border-slate-200 pt-5 sm:flex-row sm:justify-end">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isSubmitting}>
          {user.is_active ? "Save role" : "Approve account"}
        </Button>
      </div>
    </form>
  );
}
