import { useEffect, useState } from "react";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useAuth } from "@/hooks/useAuth";
import { getApiErrorMessage } from "@/lib/api-error";

interface LocationState {
  from?: { pathname?: string };
  successMessage?: string;
}

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LocationState | null;
  const [successMessage, setSuccessMessage] = useState(locationState?.successMessage ?? null);

  useEffect(() => {
    if (!successMessage) return undefined;
    const timeoutId = window.setTimeout(() => setSuccessMessage(null), 6_000);
    return () => window.clearTimeout(timeoutId);
  }, [successMessage]);

  if (!isLoading && isAuthenticated) return <Navigate to="/" replace />;

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter both your username and password.");
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await login({ username: username.trim(), password });
      void navigate(locationState?.from?.pathname ?? "/", { replace: true });
    } catch (loginError: unknown) {
      setError(getApiErrorMessage(loginError));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout>
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">Secure workspace</p>
      <h2 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">Welcome back</h2>
      <p className="mt-3 text-sm leading-6 text-slate-500">Sign in with your inventory platform credentials.</p>
      {successMessage ? (
        <div className="mt-6 flex items-start gap-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700" role="status">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {successMessage}
        </div>
      ) : null}
      <form onSubmit={(event) => void handleSubmit(event)} className="mt-8 space-y-5">
        {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700" role="alert">{error}</div> : null}
        <Input label="Username" value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" autoFocus placeholder="Enter your username" />
        <Input label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" placeholder="Enter your password" />
        <Button type="submit" isLoading={isSubmitting} className="w-full">Sign in <ArrowRight className="size-4" aria-hidden="true" /></Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        Need access?{" "}
        <Link className="font-semibold text-brand-700 underline-offset-4 hover:text-brand-800 hover:underline" to="/register">
          Create account
        </Link>
      </p>
      <p className="mt-5 text-center text-xs leading-5 text-slate-500">Access is controlled by your Django user account, groups, and permissions.</p>
    </AuthLayout>
  );
}
