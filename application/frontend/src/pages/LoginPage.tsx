import { useEffect, useState } from "react";
import { ArrowRight, Boxes, CheckCircle2, LockKeyhole, ShieldCheck } from "lucide-react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
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
    <main className="grid min-h-screen bg-ink-950 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="dashboard-grid relative hidden overflow-hidden p-12 lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -left-40 top-1/3 size-96 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="relative flex items-center gap-3 text-white">
          <span className="grid size-11 place-items-center rounded-xl bg-brand-500"><Boxes className="size-6" /></span>
          <div><p className="text-lg font-bold">Stockline</p><p className="text-xs uppercase tracking-[0.2em] text-slate-400">Inventory operations</p></div>
        </div>
        <div className="relative max-w-xl">
          <p className="text-sm font-bold uppercase tracking-[0.2em] text-brand-500">Operational clarity</p>
          <h1 className="mt-5 text-5xl font-bold leading-[1.08] tracking-tight text-white">Every item. Every warehouse. One source of truth.</h1>
          <p className="mt-6 max-w-lg text-lg leading-8 text-slate-400">A focused command center for stock, fulfillment, and order movement across your operation.</p>
          <div className="mt-10 grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur"><ShieldCheck className="size-5 text-emerald-400" /><p className="mt-4 text-sm font-semibold text-white">Role-aware access</p><p className="mt-1 text-xs leading-5 text-slate-400">Actions match backend-enforced permissions.</p></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 backdrop-blur"><LockKeyhole className="size-5 text-brand-500" /><p className="mt-4 text-sm font-semibold text-white">Secure sessions</p><p className="mt-1 text-xs leading-5 text-slate-400">JWT access with automatic refresh.</p></div>
          </div>
        </div>
        <p className="relative text-xs text-slate-600">Cloud Native Inventory Platform</p>
      </section>
      <section className="flex items-center justify-center bg-[#f7f9fc] px-5 py-12 sm:px-10">
        <div className="w-full max-w-md">
          <div className="mb-9 flex items-center gap-3 lg:hidden"><span className="grid size-10 place-items-center rounded-xl bg-brand-600 text-white"><Boxes className="size-5" /></span><span className="font-bold text-slate-950">Stockline</span></div>
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
            <Button type="submit" isLoading={isSubmitting} className="w-full">Sign in <ArrowRight className="size-4" /></Button>
          </form>
          <p className="mt-7 text-center text-xs leading-5 text-slate-400">Access is controlled by your Django user account, groups, and permissions.</p>
        </div>
      </section>
    </main>
  );
}
