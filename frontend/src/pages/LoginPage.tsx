// "/" — login screen, in Spanish, with the brand identity and "modo sencillo".
import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getSimpleMode, setSimpleMode } from "../auth/simpleMode";
import { es } from "../i18n/es";
import { AlertTriangle, Icon } from "../components/icons";
import { LogIn } from "lucide-react";

// Public demo accounts from README.md (synthetic users only).
const DEMO_USERS = [
  "owner@ejemplo.test",
  "coordinacion.a@ejemplo.test",
  "cui-001@ejemplo.test",
  "cui-003@ejemplo.test",
  "fam-0001@ejemplo.test",
];

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [simple, setSimple] = useState(getSimpleMode());
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to={user.home} replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const me = await login(email, password);
      navigate(me.home, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError && err.message ? err.message : es.login.errorGeneric);
    } finally {
      setBusy(false);
    }
  };

  const toggleSimple = (on: boolean) => {
    setSimple(on);
    setSimpleMode(on);
  };

  const input = "mt-1 block w-full min-h-12 rounded-card border-2 border-muted/60 bg-white px-3 focus:border-teal";

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <img src="/logo.svg" alt={`${es.app.name} · ${es.app.tagline}`} className="mx-auto h-20" />
        <section className="mt-8 rounded-card bg-white p-6 shadow-sm border border-teal/15">
          <h1 className="text-teal">{es.login.title}</h1>
          <p className="text-muted">{es.login.subtitle}</p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate>
            <label className="block">
              <span className="font-bold">{es.login.email}</span>
              <input
                type="email" autoComplete="username" required value={email}
                onChange={(e) => setEmail(e.target.value)} className={input}
              />
            </label>
            <label className="block">
              <span className="font-bold">{es.login.password}</span>
              <input
                type={showPassword ? "text" : "password"} autoComplete="current-password" required
                value={password} onChange={(e) => setPassword(e.target.value)} className={input}
              />
            </label>
            <label className="flex min-h-12 items-center gap-3">
              <input type="checkbox" checked={showPassword} onChange={(e) => setShowPassword(e.target.checked)}
                className="size-6 accent-teal" />
              {showPassword ? es.login.hidePassword : es.login.showPassword}
            </label>

            {error && (
              <p role="alert" className="rounded-card border-2 border-danger bg-danger/5 p-3 font-bold text-danger">
                <Icon as={AlertTriangle} /> {error}
              </p>
            )}

            <button
              type="submit" disabled={busy}
              className="w-full min-h-12 rounded-card bg-teal px-4 text-lg font-bold text-white hover:bg-teal-dark disabled:opacity-70"
            >
              <Icon as={LogIn} />{" "}
              {busy ? es.login.submitting : es.login.submit}
            </button>
          </form>

          <label className="mt-6 flex min-h-12 items-center gap-3 border-t border-teal/15 pt-4">
            <input type="checkbox" checked={simple} onChange={(e) => toggleSimple(e.target.checked)}
              className="size-6 accent-teal" />
            <span className="font-bold">{es.login.simpleMode}</span>
          </label>
        </section>

        <details className="mt-6 rounded-card border border-teal/15 bg-white p-4">
          <summary className="min-h-12 cursor-pointer font-bold text-teal flex items-center">
            {es.login.demoUsersTitle}
          </summary>
          <ul className="mt-2 space-y-1">
            {DEMO_USERS.map((u) => (
              <li key={u}>
                <button type="button" onClick={() => setEmail(u)}
                  className="min-h-12 w-full rounded-card px-2 text-left underline decoration-teal/40 hover:bg-teal/10">
                  {u}
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-muted">{es.login.demoUsersNote}</p>
        </details>
        <p className="mt-6 text-center text-muted">{es.app.syntheticData}</p>
      </div>
    </main>
  );
}
