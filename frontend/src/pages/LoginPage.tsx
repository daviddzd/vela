// "/entrar" — login screen, in Spanish, with the brand identity and "modo sencillo". "/" is the presentation page.
import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { getSimpleMode, setSimpleMode } from "../auth/simpleMode";
import { es } from "../i18n/es";
import { AlertTriangle, Icon } from "../components/icons";
import { ArrowLeft, BellRing, LogIn, MapPinned, Smartphone } from "lucide-react";
import { Highlight, IconCircle } from "../components/ui";

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

  const input = "mt-1 block w-full min-h-12 rounded-field border-2 border-muted/60 bg-white px-3 focus:border-navy";

  return (
    <main className="section-header min-h-screen lg:grid lg:grid-cols-[1fr_1.1fr]">
      {/* brand panel: deep blue, white logo, what you can do (hidden text never carries the form) */}
      <aside className="bg-deep px-4 py-3 text-white lg:flex lg:flex-col lg:justify-between lg:px-14 lg:py-14">
        <div className="flex items-center justify-between gap-4">
          <img src="/logo-white.svg" alt={`${es.app.name} · ${es.app.tagline}`} className="h-10 lg:h-12" />
          <Link to="/" aria-label={es.login.backLabel} className="inline-flex min-h-12 shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-4 font-bold text-sky hover:bg-white/10">
            <Icon as={ArrowLeft} /> {es.login.back}</Link>
        </div>
        <div className="hidden lg:block">
          <p className="font-[family-name:var(--font-display)] text-4xl font-extrabold leading-tight">{es.login.panelTitle}</p>
          <ul className="mt-8 space-y-5 text-lg text-sky">{es.login.panelPoints.map((p, i) => (
            <li key={p} className="flex items-center gap-4"><IconCircle icon={[MapPinned, Smartphone, BellRing][i]} />{p}</li>))}</ul>
        </div>
        <p className="hidden text-sky lg:block">{es.app.syntheticData}</p>
      </aside>
      <div className="flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <section className="rounded-card border border-navy/10 bg-white p-7 shadow-[var(--shadow-card)]">
          <h1 className="text-3xl"><Highlight text={es.login.title} /></h1>
          <p className="mt-1 text-muted">{es.login.subtitle}</p>

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
                className="size-6 accent-navy" />
              {showPassword ? es.login.hidePassword : es.login.showPassword}
            </label>

            {error && (
              <p role="alert" className="rounded-card border-2 border-danger bg-danger/5 p-3 font-bold text-danger">
                <Icon as={AlertTriangle} /> {error}
              </p>
            )}

            <button
              type="submit" disabled={busy}
              className="w-full min-h-12 rounded-full bg-navy px-4 text-lg font-bold text-white shadow-sm hover:bg-navy-dark disabled:opacity-70"
            >
              <Icon as={LogIn} />{" "}
              {busy ? es.login.submitting : es.login.submit}
            </button>
          </form>

          <label className="mt-6 flex min-h-12 items-center gap-3 border-t border-navy/15 pt-4">
            <input type="checkbox" checked={simple} onChange={(e) => toggleSimple(e.target.checked)}
              className="size-6 accent-navy" />
            <span className="font-bold">{es.login.simpleMode}</span>
          </label>
        </section>

        <details className="mt-6 rounded-card border border-navy/10 bg-white p-5 shadow-[var(--shadow-card)]">
          <summary className="min-h-12 cursor-pointer font-bold text-navy flex items-center">
            {es.login.demoUsersTitle}
          </summary>
          <ul className="mt-2 space-y-1">
            {DEMO_USERS.map((u) => (
              <li key={u}>
                <button type="button" onClick={() => setEmail(u)}
                  className="min-h-12 w-full rounded-field px-2 text-left underline decoration-navy/40 hover:bg-sky">
                  {u}
                </button>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-muted">{es.login.demoUsersNote}</p>
        </details>
        <p className="mt-6 text-center text-muted lg:hidden">{es.app.syntheticData}</p>
      </div>
      </div>
    </main>
  );
}
