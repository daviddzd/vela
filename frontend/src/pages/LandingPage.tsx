// "/" — public presentation page of Enlaza (fictitious company of a school project). No login needed.
// Rules: every figure has its source (CLAUDE.md rule 11); no doctors, testimonials, ratings or invented numbers;
// images are our own SVG (docs/creditos.md).
import { BarChart3, CalendarCheck, ClipboardList, FlaskConical, Lock, LogIn, Mic, ShieldCheck, Smartphone, UserCheck, Wind } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { HeroIllustration } from "../components/HeroIllustration";
import { Icon } from "../components/icons";
import { Highlight, IconCircle } from "../components/ui";
import { es } from "../i18n/es";

const t = es.landing;
const MODULE_ICON: Record<string, LucideIcon> = { operation: ClipboardList, panorama: BarChart3, sirag: FlaskConical, voice: Mic, contingency: Wind };
const HOW_ICON: LucideIcon[] = [CalendarCheck, UserCheck, Smartphone, ShieldCheck];
const pill = "inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-6 font-bold";

export function LandingPage() {
  const { user } = useAuth();
  const enter = user
    ? <Link to={user.home} className={`${pill} bg-navy text-white hover:bg-navy-dark`}><Icon as={LogIn} /> {t.goHome}</Link>
    : <Link to="/entrar" className={`${pill} bg-navy text-white hover:bg-navy-dark`}><Icon as={LogIn} /> {t.enter}</Link>;

  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-20 border-b border-navy/10 bg-white">
        <div className="mx-auto flex max-w-[66rem] items-center gap-4 px-4 py-3">
          <img src="/logo.svg" alt={`${es.app.name} · ${es.app.tagline}`} className="h-11" />
          <nav aria-label={t.nav.how} className="ml-auto hidden lg:block">
            <ul className="flex gap-1">{(["how", "modules", "plans", "privacy"] as const).map((k) => (
              <li key={k}><a href={`#${k}`} className="inline-flex min-h-12 items-center rounded-full px-4 font-bold text-navy hover:bg-sky">{t.nav[k]}</a></li>))}</ul>
          </nav>
          <div className="ml-auto lg:ml-2">{enter}</div>
        </div>
      </header>

      <main>
        {/* hero: the problem and the promise */}
        <section className="section-header">
          <div className="mx-auto grid max-w-[66rem] items-center gap-10 px-4 py-12 lg:grid-cols-[1.1fr_1fr] lg:py-20">
            <div>
              <p className="inline-flex rounded-full bg-white px-4 py-1 font-bold text-teal-text shadow-sm">{t.kicker}</p>
              <h1 className="mt-5 text-4xl sm:text-5xl"><Highlight text={t.heroTitle} /></h1>
              <p className="mt-5 text-lg text-ink">{t.heroProblem}</p>
              <p className="mt-3 text-lg font-bold text-navy">{t.heroPromise}</p>
              <div className="mt-7 flex flex-wrap gap-3">
                {enter}
                <a href="#how" className={`${pill} border-2 border-navy bg-white text-navy hover:bg-sky`}>{t.see}</a>
              </div>
            </div>
            <HeroIllustration />
          </div>
        </section>

        {/* figures with their source */}
        <section aria-labelledby="stats-title" className="bg-deep text-white">
          <div className="mx-auto max-w-[66rem] px-4 py-12">
            <h2 id="stats-title" className="text-white">{t.statsTitle}</h2>
            <ul className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">{t.stats.map((s) => (
              <li key={s.label} className="border-l-4 border-teal pl-4">
                <p className="figure text-4xl text-white">{s.value}</p>
                <p className="mt-1 text-sky">{s.label}</p>
                <p className="mt-2 text-sm text-sky">{es.panorama.sourcePrefix} {s.source}</p>
              </li>))}</ul>
          </div>
        </section>

        <section id="how" aria-labelledby="how-title" className="scroll-mt-20">
          <div className="mx-auto max-w-[66rem] px-4 py-16">
            <h2 id="how-title" className="text-3xl"><Highlight text={t.howTitle} /></h2>
            <ol className="mt-8 grid items-start gap-5 md:grid-cols-2 lg:grid-cols-4">{t.how.map((h, i) => (
              <li key={h.title} className="rounded-card border border-navy/10 bg-white p-6 shadow-[var(--shadow-card)]">
                <div className="flex items-center gap-3"><IconCircle icon={HOW_ICON[i]} /><span className="figure text-2xl text-navy">{i + 1}</span></div>
                <h3 className="mt-4 text-lg">{h.title}</h3>
                <p className="mt-2">{h.text}</p>
              </li>))}</ol>
          </div>
        </section>

        <section id="modules" aria-labelledby="modules-title" className="section-header scroll-mt-20">
          <div className="mx-auto max-w-[66rem] px-4 py-16">
            <h2 id="modules-title" className="text-3xl"><Highlight text={t.modulesTitle} /></h2>
            <ul className="mt-8 grid items-start gap-5 sm:grid-cols-2 lg:grid-cols-5">{t.modules.map((m) => (
              <li key={m.key} className="rounded-card border border-navy/10 bg-white p-6 shadow-[var(--shadow-card)]">
                <IconCircle icon={MODULE_ICON[m.key]} />
                <h3 className="mt-4 text-lg">{m.title}</h3>
                <p className="mt-2">{m.text}</p>
              </li>))}</ul>
          </div>
        </section>

        <section id="plans" aria-labelledby="plans-title" className="scroll-mt-20">
          <div className="mx-auto max-w-[66rem] px-4 py-16">
            <h2 id="plans-title" className="text-3xl"><Highlight text={t.plansTitle} /></h2>
            <ul className="mt-8 grid items-start gap-5 sm:grid-cols-3">{t.plans.map((p) => (
              <li key={p.name} className={`rounded-card bg-white p-6 shadow-[var(--shadow-card)] ${p.featured ? "border-2 border-navy" : "border border-navy/10"}`}>
                <h3 className="text-xl">{p.name}</h3>
                {p.featured && <p className="mt-1 text-sm font-bold text-teal-text">{t.featured}</p>}
                <p className="mt-3 figure text-4xl text-navy">{p.price}</p><p className="text-muted">MXN {t.perMonth}</p>
                <p className="mt-2">{p.detail}</p>
              </li>))}</ul>
            {/* phone: name and price on top, the description below; wider screens: one row */}
            <div className="mt-5 rounded-card border border-dashed border-navy/30 bg-sky-soft p-5 sm:flex sm:items-center sm:gap-6">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 sm:shrink-0">
                <h3 className="text-lg">{t.gov.name}</h3>
                <p><span className="figure text-2xl text-navy">{t.gov.price}</span> <span className="text-muted">MXN {t.perMonth}</span></p>
              </div>
              <p className="mt-2 sm:mt-0 sm:min-w-0 sm:flex-1">{t.gov.detail}</p>
            </div>
            <p className="mt-4 text-muted">{t.plansNote}</p>
          </div>
        </section>

        <section id="privacy" aria-labelledby="privacy-title" className="section-header scroll-mt-20">
          <div className="mx-auto max-w-[66rem] px-4 py-16">
            <h2 id="privacy-title" className="text-3xl"><Highlight text={t.privacyTitle} /></h2>
            <ul className="mt-8 grid items-start gap-4 md:grid-cols-2">{t.privacy.map((p) => (
              <li key={p} className="flex items-start gap-4 rounded-card border border-navy/10 bg-white p-5 shadow-[var(--shadow-card)]">
                <IconCircle icon={Lock} /><p className="pt-2">{p}</p>
              </li>))}</ul>
          </div>
        </section>

        <section aria-labelledby="cta-title">
          <div className="mx-auto max-w-[66rem] px-4 py-16">
            <div className="flex flex-wrap items-center justify-between gap-6 rounded-[32px] bg-deep p-8 text-white sm:p-12">
              <div>
                <h2 id="cta-title" className="text-3xl text-white">{t.ctaTitle.replace(/\*/g, "")}</h2>
                <p className="mt-2 text-sky">{t.ctaText}</p>
              </div>
              {user
                ? <Link to={user.home} className={`${pill} bg-white text-navy hover:bg-sky`}><Icon as={LogIn} /> {t.goHome}</Link>
                : <Link to="/entrar" className={`${pill} bg-white text-navy hover:bg-sky`}><Icon as={LogIn} /> {t.enter}</Link>}
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-deep text-sky">
        <div className="mx-auto max-w-[66rem] space-y-3 px-4 py-10">
          <img src="/logo-white.svg" alt={`${es.app.name} · ${es.app.tagline}`} className="h-10" />
          <p className="text-lg font-bold text-white">{es.app.syntheticData}</p>
          <p>{t.footerCompany}</p>
          <p className="text-sm">{t.footerCredits}</p>
        </div>
      </footer>
    </div>
  );
}
