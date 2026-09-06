import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { Link, Navigate } from "react-router-dom";
import { registerUser } from "@/api/auth-api";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage, getApiFieldErrors } from "@/lib/api-error";
import type { UserRegistrationRequest } from "@/types";

const registrationFields = [
  "username",
  "email",
  "first_name",
  "last_name",
  "password",
  "password_confirm",
] as const;

type RegistrationField = (typeof registrationFields)[number];
type RegistrationErrors = Partial<Record<RegistrationField, string>>;

const emptyForm: UserRegistrationRequest = {
  username: "",
  email: "",
  first_name: "",
  last_name: "",
  password: "",
  password_confirm: "",
};

const basicEmailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function RegisterPage() {
  const [form, setForm] = useState<UserRegistrationRequest>(emptyForm);
  const [errors, setErrors] = useState<RegistrationErrors>({});
  const [requestError, setRequestError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { isAuthenticated, isLoading } = useAuth();

  if (!isLoading && isAuthenticated) return <Navigate to="/" replace />;

  function updateField(field: RegistrationField) {
    return (event: ChangeEvent<HTMLInputElement>) => {
      const value = event.target.value;
      setForm((current) => ({ ...current, [field]: value }));
      setErrors((current) => {
        if (!current[field]) return current;
        const next = { ...current };
        delete next[field];
        return next;
      });
      setRequestError(null);
    };
  }

  function validateForm(): RegistrationErrors {
    const nextErrors: RegistrationErrors = {};
    const email = form.email.trim();

    if (!form.username.trim()) nextErrors.username = "Username is required.";
    if (!email) nextErrors.email = "Email is required.";
    else if (!basicEmailPattern.test(email)) nextErrors.email = "Enter a valid email address.";
    if (!form.password) nextErrors.password = "Password is required.";
    if (!form.password_confirm) {
      nextErrors.password_confirm = "Confirm your password.";
    } else if (form.password !== form.password_confirm) {
      nextErrors.password_confirm = "Passwords do not match.";
    }

    return nextErrors;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      setRequestError(null);
      return;
    }

    setIsSubmitting(true);
    setErrors({});
    setRequestError(null);

    try {
      const response = await registerUser({
        username: form.username.trim(),
        email: form.email.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        password: form.password,
        password_confirm: form.password_confirm,
      });
      setForm(emptyForm);
      setSuccessMessage(response.detail);
    } catch (error: unknown) {
      const fieldErrors = getApiFieldErrors(error, registrationFields);
      setErrors(fieldErrors);
      if (Object.keys(fieldErrors).length === 0) setRequestError(getApiErrorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  if (successMessage) {
    return (
      <AuthLayout>
        <div className="py-4 text-center" role="status" aria-live="polite">
          <span className="mx-auto grid size-12 place-items-center rounded-full bg-emerald-100 text-emerald-700">
            <CheckCircle2 className="size-6" aria-hidden="true" />
          </span>
          <p className="mt-6 text-xs font-bold uppercase tracking-[0.18em] text-emerald-700">Request submitted</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">Account created successfully</h2>
          <p className="mt-4 text-sm leading-6 text-slate-600">{successMessage}</p>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            You can sign in after an administrator activates your account.
          </p>
          <Link
            to="/login"
            className="mt-8 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-brand-600 bg-brand-600 px-4 text-sm font-semibold text-white shadow-sm transition-colors hover:border-brand-700 hover:bg-brand-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500/60 focus-visible:ring-offset-2 motion-reduce:transition-none"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to Sign In
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout contentWidth="lg">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">Request access</p>
      <h2 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">Create your account</h2>
      <p className="mt-3 text-sm leading-6 text-slate-500">
        Submit your details for administrator approval. No access role is assigned during registration.
      </p>
      <form onSubmit={(event) => void handleSubmit(event)} className="mt-8 space-y-5" noValidate>
        {requestError ? (
          <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700" role="alert">
            {requestError}
          </div>
        ) : null}
        <div className="grid gap-5 sm:grid-cols-2">
          <Input
            label="Username"
            value={form.username}
            onChange={updateField("username")}
            error={errors.username}
            autoComplete="username"
            autoCapitalize="none"
            spellCheck={false}
            autoFocus
            required
            placeholder="Choose a username"
          />
          <Input
            label="Email"
            type="email"
            value={form.email}
            onChange={updateField("email")}
            error={errors.email}
            autoComplete="email"
            autoCapitalize="none"
            spellCheck={false}
            required
            placeholder="you@example.com"
          />
          <Input
            label="First name (optional)"
            value={form.first_name}
            onChange={updateField("first_name")}
            error={errors.first_name}
            autoComplete="given-name"
            dir="auto"
            placeholder="Your first name"
          />
          <Input
            label="Last name (optional)"
            value={form.last_name}
            onChange={updateField("last_name")}
            error={errors.last_name}
            autoComplete="family-name"
            dir="auto"
            placeholder="Your last name"
          />
          <Input
            label="Password"
            type="password"
            value={form.password}
            onChange={updateField("password")}
            error={errors.password}
            autoComplete="new-password"
            required
            placeholder="Create a strong password"
          />
          <Input
            label="Confirm password"
            type="password"
            value={form.password_confirm}
            onChange={updateField("password_confirm")}
            error={errors.password_confirm}
            autoComplete="new-password"
            required
            placeholder="Repeat your password"
          />
        </div>
        <Button type="submit" isLoading={isSubmitting} className="w-full">
          Create account
          <ArrowRight className="size-4" aria-hidden="true" />
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an approved account?{" "}
        <Link className="font-semibold text-brand-700 underline-offset-4 hover:text-brand-800 hover:underline" to="/login">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
