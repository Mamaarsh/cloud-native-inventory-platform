import { useState } from "react";
import { CheckCircle2, KeyRound, LockKeyhole, Mail, Pencil, ShieldCheck, UserRound } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { changeCurrentUserPassword } from "@/api/auth-api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage, getApiFieldErrors } from "@/lib/api-error";
import {
  ROLES,
  type PasswordChangeRequest,
  type User,
  type UserProfileUpdateRequest,
} from "@/types";

const emptyPasswordForm: PasswordChangeRequest = {
  current_password: "",
  new_password: "",
  new_password_confirm: "",
};

const passwordFields = [
  "current_password",
  "new_password",
  "new_password_confirm",
] as const;

type PasswordField = (typeof passwordFields)[number];
type PasswordErrors = Partial<Record<PasswordField, string>>;

function profileValues(user: User | null): UserProfileUpdateRequest {
  return {
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    email: user?.email ?? "",
  };
}

export function AccountPage() {
  const { currentUser, hasRole, logout, updateProfile } = useAuth();
  const navigate = useNavigate();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState<UserProfileUpdateRequest>(() => profileValues(currentUser));
  const [saveError, setSaveError] = useState<unknown>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [isPasswordSaving, setIsPasswordSaving] = useState(false);
  const [passwordForm, setPasswordForm] = useState<PasswordChangeRequest>(emptyPasswordForm);
  const [passwordErrors, setPasswordErrors] = useState<PasswordErrors>({});
  const [passwordRequestError, setPasswordRequestError] = useState<unknown>(null);

  if (!currentUser) return null;

  const fullName = [currentUser.first_name, currentUser.last_name].filter(Boolean).join(" ");
  const initials = (fullName || currentUser.username)
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  const primaryRole = Object.values(ROLES).find((role) => hasRole(role))
    ?? currentUser.groups[0];

  function beginEditing(): void {
    setForm(profileValues(currentUser));
    setSaveError(null);
    setSuccessMessage(null);
    setIsEditing(true);
  }

  function cancelEditing(): void {
    setForm(profileValues(currentUser));
    setSaveError(null);
    setIsEditing(false);
  }

  async function saveProfile(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (isSaving) return;

    setIsSaving(true);
    setSaveError(null);
    setSuccessMessage(null);
    try {
      const updatedUser = await updateProfile({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        email: form.email.trim(),
      });
      setForm(profileValues(updatedUser));
      setIsEditing(false);
      setSuccessMessage("Your profile was updated successfully.");
    } catch (error: unknown) {
      setSaveError(error);
    } finally {
      setIsSaving(false);
    }
  }

  function beginPasswordChange(): void {
    setPasswordForm(emptyPasswordForm);
    setPasswordErrors({});
    setPasswordRequestError(null);
    setIsChangingPassword(true);
  }

  function cancelPasswordChange(): void {
    setPasswordForm(emptyPasswordForm);
    setPasswordErrors({});
    setPasswordRequestError(null);
    setIsChangingPassword(false);
  }

  function updatePasswordField(field: PasswordField, value: string): void {
    setPasswordForm((current) => ({ ...current, [field]: value }));
    setPasswordErrors((current) => ({ ...current, [field]: undefined }));
    setPasswordRequestError(null);
  }

  async function changePassword(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (isPasswordSaving) return;

    const nextErrors: PasswordErrors = {};
    if (!passwordForm.current_password) nextErrors.current_password = "Current password is required.";
    if (!passwordForm.new_password) nextErrors.new_password = "New password is required.";
    if (!passwordForm.new_password_confirm) {
      nextErrors.new_password_confirm = "Confirm your new password.";
    } else if (passwordForm.new_password !== passwordForm.new_password_confirm) {
      nextErrors.new_password_confirm = "New passwords do not match.";
    }
    setPasswordErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setIsPasswordSaving(true);
    setPasswordRequestError(null);
    try {
      const response = await changeCurrentUserPassword(passwordForm);
      setPasswordForm(emptyPasswordForm);
      logout();
      void navigate("/login", {
        replace: true,
        state: {
          successMessage: `${response.detail} Sign in with your new password.`,
        },
      });
    } catch (error: unknown) {
      const fieldErrors = getApiFieldErrors(error, passwordFields);
      setPasswordErrors(fieldErrors);
      if (Object.keys(fieldErrors).length === 0) setPasswordRequestError(error);
    } finally {
      setIsPasswordSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="My Account"
        description="Your authenticated identity and access information from the inventory platform."
      />

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 bg-slate-50/70 px-6 py-5">
            <div>
              <h3 className="font-bold text-slate-950">Profile</h3>
              <p className="mt-1 text-xs text-slate-500">Information returned by `/api/auth/me/`</p>
            </div>
            {!isEditing ? (
              <Button size="sm" variant="outline" onClick={beginEditing}>
                <Pencil className="size-4" aria-hidden="true" /> Edit Profile
              </Button>
            ) : null}
          </div>
          <div className="p-6">
            {successMessage ? (
              <div className="mb-6 flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">
                <CheckCircle2 className="size-4 shrink-0" aria-hidden="true" />
                {successMessage}
              </div>
            ) : null}
            <div className="flex items-center gap-4 border-b border-slate-100 pb-6">
              <span className="grid size-16 shrink-0 place-items-center rounded-2xl bg-slate-900 text-lg font-bold text-white">
                {initials}
              </span>
              <div className="min-w-0">
                <p dir="auto" className="truncate text-xl font-bold text-slate-950">
                  {fullName || currentUser.username}
                </p>
                <p dir="auto" className="mt-1 truncate text-sm text-slate-500">
                  @{currentUser.username}
                </p>
              </div>
            </div>

            {isEditing ? (
              <form onSubmit={(event) => void saveProfile(event)} className="mt-6 space-y-5">
                {saveError ? (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
                    {getApiErrorMessage(saveError)}
                  </div>
                ) : null}
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input
                    label="First name"
                    dir="auto"
                    value={form.first_name}
                    onChange={(event) => {
                      setForm((current) => ({ ...current, first_name: event.target.value }));
                      setSaveError(null);
                    }}
                    autoComplete="given-name"
                    autoFocus
                  />
                  <Input
                    label="Last name"
                    dir="auto"
                    value={form.last_name}
                    onChange={(event) => {
                      setForm((current) => ({ ...current, last_name: event.target.value }));
                      setSaveError(null);
                    }}
                    autoComplete="family-name"
                  />
                </div>
                <Input
                  label="Email"
                  type="email"
                  value={form.email}
                  onChange={(event) => {
                    setForm((current) => ({ ...current, email: event.target.value }));
                    setSaveError(null);
                  }}
                  autoComplete="email"
                />
                <p className="rounded-xl bg-slate-100 px-4 py-3 text-xs leading-5 text-slate-500">
                  Username and access settings are managed separately and cannot be edited here.
                </p>
                <div className="flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-5">
                  <Button variant="outline" onClick={cancelEditing} disabled={isSaving}>Cancel</Button>
                  <Button type="submit" isLoading={isSaving}>Save changes</Button>
                </div>
              </form>
            ) : (
              <dl className="mt-6 grid gap-5 sm:grid-cols-2">
                <div>
                  <dt className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                    <UserRound className="size-4" aria-hidden="true" /> Username
                  </dt>
                  <dd dir="auto" className="mt-2 text-sm font-semibold text-slate-900">
                    {currentUser.username}
                  </dd>
                </div>
                {currentUser.email ? (
                  <div>
                    <dt className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                      <Mail className="size-4" aria-hidden="true" /> Email
                    </dt>
                    <dd className="mt-2 break-all text-sm font-semibold text-slate-900">
                      {currentUser.email}
                    </dd>
                  </div>
                ) : null}
                {currentUser.first_name ? (
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wider text-slate-500">First name</dt>
                    <dd dir="auto" className="mt-2 text-sm font-semibold text-slate-900">
                      {currentUser.first_name}
                    </dd>
                  </div>
                ) : null}
                {currentUser.last_name ? (
                  <div>
                    <dt className="text-xs font-bold uppercase tracking-wider text-slate-500">Last name</dt>
                    <dd dir="auto" className="mt-2 text-sm font-semibold text-slate-900">
                      {currentUser.last_name}
                    </dd>
                  </div>
                ) : null}
                <div>
                  <dt className="text-xs font-bold uppercase tracking-wider text-slate-500">Staff access</dt>
                  <dd className="mt-2">
                    <Badge tone={currentUser.is_staff ? "blue" : "slate"}>
                      {currentUser.is_staff ? "Enabled" : "Not enabled"}
                    </Badge>
                  </dd>
                </div>
              </dl>
            )}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="p-6">
            <div className="flex items-start gap-3">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
                <ShieldCheck className="size-5" aria-hidden="true" />
              </span>
              <div>
                <h3 className="font-bold text-slate-950">Role &amp; Access</h3>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  Access is assigned through Django Groups and enforced by the API.
                </p>
              </div>
            </div>
            {currentUser.groups.length > 0 ? (
              <div className="mt-5 flex flex-wrap gap-2">
                {currentUser.groups.map((group) => (
                  <Badge key={group} tone={group === primaryRole ? "blue" : "slate"}>
                    {group}
                  </Badge>
                ))}
              </div>
            ) : (
              <p className="mt-5 rounded-xl bg-slate-100 p-3 text-sm text-slate-600">
                No Django group is currently assigned.
              </p>
            )}
            <p className="mt-4 text-xs leading-5 text-slate-500">
              Frontend controls reflect your groups; backend permissions remain authoritative.
            </p>
          </Card>

          <Card className="p-6">
            <div className="flex items-start gap-3">
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-slate-100 text-slate-600">
                <LockKeyhole className="size-5" aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-bold text-slate-950">Change Password</h3>
                </div>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  Use your current password to securely set a new one.
                </p>
                {!isChangingPassword ? (
                  <Button size="sm" variant="outline" className="mt-5" onClick={beginPasswordChange}>
                    <KeyRound className="size-4" aria-hidden="true" /> Change Password
                  </Button>
                ) : null}
              </div>
            </div>
            {isChangingPassword ? (
              <form onSubmit={(event) => void changePassword(event)} className="mt-6 space-y-4" noValidate>
                {passwordRequestError ? (
                  <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" role="alert">
                    {getApiErrorMessage(passwordRequestError)}
                  </div>
                ) : null}
                <Input
                  label="Current password"
                  type="password"
                  value={passwordForm.current_password}
                  onChange={(event) => updatePasswordField("current_password", event.target.value)}
                  error={passwordErrors.current_password}
                  autoComplete="current-password"
                  required
                  autoFocus
                />
                <Input
                  label="New password"
                  type="password"
                  value={passwordForm.new_password}
                  onChange={(event) => updatePasswordField("new_password", event.target.value)}
                  error={passwordErrors.new_password}
                  autoComplete="new-password"
                  required
                />
                <Input
                  label="Confirm new password"
                  type="password"
                  value={passwordForm.new_password_confirm}
                  onChange={(event) => updatePasswordField("new_password_confirm", event.target.value)}
                  error={passwordErrors.new_password_confirm}
                  autoComplete="new-password"
                  required
                />
                <p className="text-xs leading-5 text-slate-500">
                  Password strength requirements are validated securely by the server.
                </p>
                <div className="flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-5">
                  <Button variant="outline" onClick={cancelPasswordChange} disabled={isPasswordSaving}>
                    Cancel
                  </Button>
                  <Button type="submit" isLoading={isPasswordSaving}>
                    Change Password
                  </Button>
                </div>
              </form>
            ) : null}
          </Card>
        </div>
      </div>
    </>
  );
}
