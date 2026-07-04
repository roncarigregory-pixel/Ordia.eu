import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";
import { useI18n, LanguageToggle } from "@/context/I18nContext";
import {
  Sparkles, ArrowRight, PlayCircle, Clock, ShieldCheck, Inbox, Plug, Zap,
  MessageCircle, Mail, FileText, Sheet, Camera, Mic, CheckCircle2, Cpu, Send,
} from "lucide-react";

const POSTER = "https://static.prod-images.emergentagent.com/jobs/a5624b55-271e-475e-b7f2-289728dea1db/images/a948ca6385b0a67de5e0c7210fd6dcf546b499f2df671ced7bbdf3cced50119f.png";
const fade = (d = 0) => ({ initial: { opacity: 0, y: 16 }, whileInView: { opacity: 1, y: 0 }, viewport: { once: true }, transition: { duration: 0.5, delay: d } });

export default function Landing() {
  const { t } = useI18n();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const tryDemo = async () => {
    setLoading(true);
    try {
      await login("demo@ordia.app", "demo123");
      navigate("/app");
    } catch {
      toast.error("Demo unavailable — please try again.");
      setLoading(false);
    }
  };

  const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });

  const steps = [
    { icon: Inbox, t: t("how.s1.t"), d: t("how.s1.d") },
    { icon: Cpu, t: t("how.s2.t"), d: t("how.s2.d") },
    { icon: Send, t: t("how.s3.t"), d: t("how.s3.d") },
  ];
  const benefits = [
    { icon: Clock, t: t("ben.1.t"), d: t("ben.1.d") },
    { icon: ShieldCheck, t: t("ben.2.t"), d: t("ben.2.d") },
    { icon: Inbox, t: t("ben.3.t"), d: t("ben.3.d") },
    { icon: Plug, t: t("ben.4.t"), d: t("ben.4.d") },
  ];
  const channels = [
    { icon: MessageCircle, l: t("chan.wa") }, { icon: Mail, l: t("chan.email") },
    { icon: FileText, l: t("chan.pdf") }, { icon: Sheet, l: t("chan.xls") },
    { icon: Camera, l: t("chan.photo") }, { icon: Mic, l: t("chan.voice") },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground" data-testid="landing-page">
      {/* Top bar */}
      <header className="sticky top-0 z-50 border-b border-border/60 bg-background/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-base font-extrabold text-primary-foreground">O</div>
            <span className="font-display text-xl font-bold tracking-tight">Ordia</span>
          </div>
          <nav className="hidden items-center gap-7 text-sm font-medium text-muted-foreground md:flex">
            <button onClick={() => scrollTo("how")} className="transition-colors hover:text-foreground">{t("nav.how")}</button>
            <button onClick={() => scrollTo("benefits")} className="transition-colors hover:text-foreground">{t("nav.benefits")}</button>
          </nav>
          <div className="flex items-center gap-2.5">
            <LanguageToggle />
            <button onClick={() => navigate("/login")} data-testid="landing-login" className="hidden rounded-lg px-3 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-secondary sm:block">{t("nav.login")}</button>
            <button onClick={tryDemo} disabled={loading} data-testid="landing-nav-demo" className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground transition-transform hover:scale-[1.03] disabled:opacity-60">{t("nav.demo")}</button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute -top-24 left-1/2 h-[420px] w-[820px] -translate-x-1/2 rounded-full bg-ai/10 blur-3xl" />
        <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 py-16 lg:grid-cols-2 lg:py-24">
          <motion.div {...fade()}>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-ai-soft px-3 py-1 text-xs font-semibold text-ai">
              <Sparkles size={13} /> {t("hero.badge")}
            </span>
            <h1 className="mt-5 font-display text-4xl font-extrabold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              {t("hero.title")}
            </h1>
            <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">{t("hero.sub")}</p>
            <div data-testid="hero-positioning" className="mt-5 flex items-start gap-3 rounded-xl border border-ai/20 bg-ai-soft/60 px-4 py-3">
              <Plug size={18} className="mt-0.5 shrink-0 text-ai" />
              <div>
                <p className="text-sm font-semibold text-foreground">{t("hero.positioning")}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">{t("hero.notErp")} {t("hero.notErp.d")}</p>
              </div>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <button onClick={tryDemo} disabled={loading} data-testid="landing-hero-demo" className="group inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/20 transition-transform hover:scale-[1.03] disabled:opacity-60">
                {loading ? t("hero.cta.loading") : t("hero.cta")}
                <ArrowRight size={17} className="transition-transform group-hover:translate-x-0.5" />
              </button>
              <button onClick={() => scrollTo("video")} data-testid="landing-hero-watch" className="inline-flex items-center gap-2 rounded-xl border border-border bg-white px-6 py-3.5 text-sm font-semibold transition-colors hover:bg-secondary">
                <PlayCircle size={18} /> {t("hero.watch")}
              </button>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">{t("hero.trust")}</p>
          </motion.div>

          <motion.div {...fade(0.15)} id="video" className="scroll-mt-24">
            <div className="overflow-hidden rounded-2xl border border-border bg-black shadow-2xl shadow-primary/10">
              <video data-testid="landing-video" className="aspect-video w-full" controls preload="metadata" poster={POSTER}>
                <source src="/ordia-tutorial-16x9.mp4" type="video/mp4" />
              </video>
            </div>
          </motion.div>
        </div>

        {/* Stats strip */}
        <div className="mx-auto max-w-6xl px-5 pb-4">
          <div className="grid grid-cols-1 gap-4 rounded-2xl border border-border bg-white p-6 sm:grid-cols-3">
            {[["5+", t("hero.stat1")], ["90%", t("hero.stat2")], ["6", t("hero.stat3")]].map(([n, l]) => (
              <div key={l} className="text-center">
                <div className="font-display text-3xl font-extrabold text-primary">{n}</div>
                <div className="mt-1 text-sm text-muted-foreground">{l}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Works with your ERP — positioning */}
      <section id="erp" className="scroll-mt-20 bg-white py-20">
        <div className="mx-auto max-w-6xl px-5">
          <motion.div {...fade()} className="max-w-2xl">
            <span className="text-sm font-semibold uppercase tracking-wide text-ai">{t("erp.kicker")}</span>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight sm:text-4xl">{t("erp.title")}</h2>
            <p className="mt-3 text-base text-muted-foreground">{t("erp.sub")}</p>
            <p className="mt-3 text-lg font-semibold text-foreground">{t("erp.anyErp")}</p>
          </motion.div>
          <div className="mt-10 grid gap-5 sm:grid-cols-3">
            {[
              { icon: ShieldCheck, t: t("erp.b1.t"), d: t("erp.b1.d") },
              { icon: Cpu, t: t("erp.b2.t"), d: t("erp.b2.d") },
              { icon: Plug, t: t("erp.b3.t"), d: t("erp.b3.d") },
            ].map((b, i) => (
              <motion.div key={b.t} {...fade(i * 0.08)} className="rounded-2xl border border-border bg-secondary/30 p-6">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-ai-soft text-ai"><b.icon size={20} /></div>
                <h3 className="mt-4 font-bold">{b.t}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{b.d}</p>
              </motion.div>
            ))}
          </div>

          {/* Ordia Bridge — the moat */}
          <motion.div {...fade(0.1)} className="mt-6 overflow-hidden rounded-2xl border border-ai/20 bg-[#0f1729] text-white">
            <div className="grid gap-6 p-7 sm:p-9 lg:grid-cols-[1.3fr_1fr] lg:items-center">
              <div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-ai/20 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-ai">
                  <Plug size={13} /> {t("erp.bridge.badge")}
                </span>
                <h3 className="mt-3 font-display text-2xl font-bold tracking-tight sm:text-3xl">{t("erp.bridge.title")}</h3>
                <p className="mt-3 text-sm leading-relaxed text-white/70">{t("erp.bridge.d")}</p>
              </div>
              <div className="space-y-3">
                {[
                  { icon: Cpu, label: t("erp.bridge.p1") },
                  { icon: Zap, label: t("erp.bridge.p2") },
                  { icon: ShieldCheck, label: t("erp.bridge.p3") },
                ].map((p) => (
                  <div key={p.label} className="flex items-center gap-3 rounded-xl bg-white/5 px-4 py-3 ring-1 ring-white/10">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-ai/20 text-ai"><p.icon size={18} /></span>
                    <span className="text-sm font-medium">{p.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          <motion.p {...fade(0.15)} className="mt-6 text-center text-sm font-medium text-muted-foreground">
            {t("vision.line")}
          </motion.p>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="scroll-mt-20 bg-white py-20">
        <div className="mx-auto max-w-6xl px-5">
          <motion.div {...fade()} className="max-w-2xl">
            <span className="text-sm font-semibold uppercase tracking-wide text-ai">{t("how.kicker")}</span>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight sm:text-4xl">{t("how.title")}</h2>
          </motion.div>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {steps.map((s, i) => (
              <motion.div key={s.t} {...fade(i * 0.1)} className="relative rounded-2xl border border-border bg-secondary/30 p-6">
                <div className="absolute right-5 top-5 font-display text-4xl font-extrabold text-border">{i + 1}</div>
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary text-primary-foreground"><s.icon size={20} /></div>
                <h3 className="mt-4 text-lg font-bold">{s.t}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{s.d}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section id="benefits" className="scroll-mt-20 py-20">
        <div className="mx-auto max-w-6xl px-5">
          <motion.div {...fade()} className="max-w-2xl">
            <span className="text-sm font-semibold uppercase tracking-wide text-ai">{t("ben.kicker")}</span>
            <h2 className="mt-2 font-display text-3xl font-bold tracking-tight sm:text-4xl">{t("ben.title")}</h2>
          </motion.div>
          <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {benefits.map((b, i) => (
              <motion.div key={b.t} {...fade(i * 0.08)} className="rounded-2xl border border-border bg-white p-6 transition-shadow hover:shadow-lg hover:shadow-primary/5">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-ai-soft text-ai"><b.icon size={20} /></div>
                <h3 className="mt-4 font-bold">{b.t}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{b.d}</p>
              </motion.div>
            ))}
          </div>

          {/* Channels */}
          <motion.div {...fade()} className="mt-12 rounded-2xl border border-border bg-white p-8">
            <p className="text-center text-sm font-semibold text-muted-foreground">{t("chan.title")}</p>
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              {channels.map((c) => (
                <div key={c.l} className="flex items-center gap-2 rounded-full border border-border bg-secondary/40 px-4 py-2 text-sm font-medium">
                  <c.icon size={16} className="text-ai" /> {c.l}
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-5 pb-20">
        <motion.div {...fade()} className="mx-auto max-w-5xl overflow-hidden rounded-3xl bg-primary px-6 py-14 text-center text-primary-foreground">
          <h2 className="mx-auto max-w-2xl font-display text-3xl font-bold tracking-tight sm:text-4xl">{t("cta.title")}</h2>
          <p className="mx-auto mt-3 max-w-xl text-primary-foreground/80">{t("cta.sub")}</p>
          <button onClick={tryDemo} disabled={loading} data-testid="landing-cta-demo" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3.5 text-sm font-bold text-primary transition-transform hover:scale-[1.04] disabled:opacity-60">
            {loading ? t("hero.cta.loading") : t("cta.button")} <ArrowRight size={17} />
          </button>
          <div className="mt-6 flex items-center justify-center gap-2 text-xs text-primary-foreground/70">
            <CheckCircle2 size={14} /> {t("hero.trust")}
          </div>
        </motion.div>
      </section>

      <footer className="border-t border-border py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-5 sm:flex-row">
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-xs font-extrabold text-primary-foreground">O</div>
            <span className="font-display font-bold">Ordia</span>
            <span className="text-sm text-muted-foreground">— {t("foot.tag")}</span>
          </div>
          <LanguageToggle />
        </div>
      </footer>
    </div>
  );
}
