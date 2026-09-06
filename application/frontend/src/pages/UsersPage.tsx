import { useState } from "react";
import { ShieldCheck, UserCheck, UsersRound } from "lucide-react";
import { UserAccessForm } from "@/components/users/UserAccessForm";
import { BackgroundFetchIndicator } from "@/components/ui/BackgroundFetchIndicator";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorMessage } from "@/components/ui/ErrorMessage";
import { Modal } from "@/components/ui/Modal";
import { PageHeader } from "@/components/ui/PageHeader";
import { Pagination } from "@/components/ui/Pagination";
import { Spinner } from "@/components/ui/Spinner";
import { useAdminUsers, useUpdateAdminUser } from "@/hooks/useAdminUsers";
import { useSuccessFeedback } from "@/hooks/useSuccessFeedback";
import { formatDate } from "@/lib/format";
import { getApplicationRoles } from "@/lib/roles";
import type { AdminUser, AdminUserStatus, Role } from "@/types";

interface StatusFilterOption {
  label: string;
  value: AdminUserStatus | undefined;
}

const statusFilters: StatusFilterOption[] = [
  { label: "All users", value: undefined },
  { label: "Pending", value: "pending" },
  { label: "Active", value: "active" },
];

export function UsersPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<AdminUserStatus>();
  const [managedUser, setManagedUser] = useState<AdminUser | null>(null);
  const users = useAdminUsers({ page, status: statusFilter });
  const updateMutation = useUpdateAdminUser();
  const { showSuccess } = useSuccessFeedback();

  function openAccessManagement(user: AdminUser): void {
    updateMutation.reset();
    setManagedUser(user);
  }

  function closeAccessManagement(): void {
    if (updateMutation.isPending) return;
    setManagedUser(null);
    updateMutation.reset();
  }

  async function updateUserAccess(role: Role): Promise<void> {
    if (!managedUser) return;
    const approving = !managedUser.is_active;

    try {
      await updateMutation.mutateAsync({
        id: managedUser.id,
        payload: approving ? { is_active: true, role } : { role },
      });
    } catch {
      return;
    }

    setManagedUser(null);
    showSuccess(
      approving
        ? "User approved successfully."
        : "User role updated successfully.",
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Access control"
        title="User management"
        description="Review account requests, approve access, and manage application roles."
      />

      <Card className="overflow-hidden" aria-busy={users.isPending}>
        <div className="flex flex-col gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="overflow-x-auto">
            <div className="inline-flex min-w-max gap-1 rounded-xl border border-slate-200 bg-white p-1 shadow-sm" role="group" aria-label="Filter users by account status">
              {statusFilters.map((filter) => {
                const selected = statusFilter === filter.value;
                return (
                  <button
                    key={filter.label}
                    type="button"
                    aria-pressed={selected}
                    onClick={() => {
                      setStatusFilter(filter.value);
                      setPage(1);
                    }}
                    className={`min-h-9 rounded-lg px-3 text-sm font-semibold transition-colors motion-reduce:transition-none ${
                      selected
                        ? "bg-brand-50 text-brand-700 ring-1 ring-inset ring-brand-100"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-950"
                    }`}
                  >
                    {filter.label}
                  </button>
                );
              })}
            </div>
          </div>
          <p className="w-fit rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 shadow-sm">
            {users.data?.count ?? 0} accounts
          </p>
        </div>

        <BackgroundFetchIndicator
          active={users.isFetching && !users.isPending}
          label="Updating users"
        />

        {users.isPending ? <Spinner label="Loading users" /> : null}
        {users.isError ? (
          <div className="p-5">
            <ErrorMessage
              error={users.error}
              onRetry={() => void users.refetch()}
              title="Unable to load users"
            />
          </div>
        ) : null}

        {users.data?.results.length === 0 ? (
          <EmptyState
            icon={UsersRound}
            title={statusFilter === "pending" ? "No pending accounts" : "No users found"}
            description={
              statusFilter === "pending"
                ? "There are no account requests awaiting approval."
                : statusFilter === "active"
                  ? "There are no active accounts to display."
                  : "No user accounts are currently available."
            }
          />
        ) : null}

        {users.data && users.data.results.length > 0 ? (
          <>
            <div className="table-scroll overflow-x-auto">
              <table className="w-full min-w-[960px] text-left">
                <thead className="border-y border-slate-200 bg-slate-100/80 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600">
                  <tr>
                    <th scope="col" className="px-6 py-4">User</th>
                    <th scope="col" className="px-6 py-4">Name</th>
                    <th scope="col" className="px-6 py-4">Role</th>
                    <th scope="col" className="px-6 py-4">Account status</th>
                    <th scope="col" className="px-6 py-4">Joined</th>
                    <th scope="col" className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70">
                  {users.data.results.map((user) => {
                    const displayName = [user.first_name, user.last_name]
                      .filter(Boolean)
                      .join(" ");
                    const applicationRoles = getApplicationRoles(user.groups);

                    return (
                      <tr key={user.id} className="transition-colors hover:bg-brand-50/35 motion-reduce:transition-none">
                        <td className="px-6 py-4">
                          <p className="font-semibold text-slate-900">{user.username}</p>
                          <p className="mt-0.5 max-w-64 break-all text-xs text-slate-500">
                            {user.email || "No email provided"}
                          </p>
                        </td>
                        <td className="px-6 py-4">
                          <span dir="auto" className={displayName ? "text-sm font-medium text-slate-800" : "text-sm text-slate-500"}>
                            {displayName || "Not provided"}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {applicationRoles.length > 0 ? (
                            <div className="flex flex-wrap gap-1.5">
                              {applicationRoles.map((role) => <Badge key={role} tone="blue">{role}</Badge>)}
                            </div>
                          ) : (
                            <span className="text-sm text-slate-500">No role assigned</span>
                          )}
                        </td>
                        <td className="px-6 py-4">
                          <Badge tone={user.is_active ? "green" : "amber"}>
                            <span className={`size-1.5 rounded-full ${user.is_active ? "bg-emerald-500" : "bg-amber-500"}`} aria-hidden="true" />
                            {user.is_active ? "Active" : "Pending"}
                          </Badge>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-500">{formatDate(user.date_joined)}</td>
                        <td className="px-6 py-4 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openAccessManagement(user)}
                          >
                            {user.is_active ? (
                              <ShieldCheck className="size-4" aria-hidden="true" />
                            ) : (
                              <UserCheck className="size-4" aria-hidden="true" />
                            )}
                            {user.is_active
                              ? applicationRoles.length > 0
                                ? "Manage role"
                                : "Assign role"
                              : "Review account"}
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="border-t border-slate-200 bg-slate-50/50 px-6 py-4">
              <Pagination
                page={page}
                count={users.data.count}
                hasNext={Boolean(users.data.next)}
                hasPrevious={Boolean(users.data.previous)}
                onPageChange={setPage}
              />
            </div>
          </>
        ) : null}
      </Card>

      <Modal
        open={Boolean(managedUser)}
        onClose={closeAccessManagement}
        title={managedUser?.is_active ? "Manage user role" : "Approve account"}
        description={
          managedUser?.is_active
            ? "Assign one application role using backend-enforced access controls."
            : "Choose the access role to grant when this account is activated."
        }
        size="sm"
        isBusy={updateMutation.isPending}
      >
        {managedUser ? (
          <UserAccessForm
            key={managedUser.id}
            user={managedUser}
            isSubmitting={updateMutation.isPending}
            serverError={updateMutation.error}
            onSubmit={updateUserAccess}
            onCancel={closeAccessManagement}
            onResetError={updateMutation.reset}
          />
        ) : null}
      </Modal>
    </>
  );
}
