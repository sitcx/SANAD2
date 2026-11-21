import { createFileRoute, Link } from '@tanstack/react-router';
import type { AccountRole } from '@/lib/sanad-state';
import { ArrowLeft, Building2, BriefcaseBusiness, UserRound, ClipboardCheck, FileUser, HandMetal, Search, CalendarDays, Compass, Filter, LifeBuoy, TrendingUp, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SiteFooter } from '@/components/sanad-layout';
import { LandingDock } from '@/components/landing-dock';
import { FeatureIllustration } from '@/components/landing-illustrations';
import { ScrollReveal } from '@/components/scroll-reveal';
import { HeroPreview } from '@/components/hero-preview';
import { candidateJourney, companyJourney, type JourneyIcon } from '@/lib/sanad-data';
import { useState } from 'react';
import { useSanad } from '@/lib/sanad-context';
import { pageHead } from '@/lib/page-head';

// A bundled gateway has no absolute public URL; hosting supplies the social preview.
export const Route = createFileRoute("/")({
  head: () => pageHead('سَند.. حيث تلتقي الكفاءة بالفرصة', 'منصة توظيف ذكية تمكّن الصم والمكفوفين من الوصول إلى الفرص المناسبة لمهاراتهم، وتُمكّن جهات التوظيف من استقطاب كفاءاتهم، من التقديم حتى ما بعد التوظيف.'),
  component: Index,
});

type LandingFeature = { kind: 'jobs' | 'support' | 'interview'; title: string; text: string; soon?: boolean };
const features: LandingFeature[] = [
  { kind: 'jobs', title: 'الوظائف المناسبة وخطة التهيئة', text: 'تحليل سيرتك، وترشيح وظائف تناسب مهاراتك، مع عرض التسهيلات المطلوبة لكل وظيفة.' },
  { kind: 'interview', title: 'المقابلة الذكية', text: 'مقابلة بلغة الإشارة بمترجم ذكي أو بشري، يختار فيها المرشح الجملة الصحيحة قبل إرسالها، أو مقابلة صوتية للمكفوفين.' },
  { kind: 'support', title: 'الدعم بعد التوظيف', text: 'ارفع طلب دعم متى احتجت، مثل مترجم إشارة لاجتماع أو تهيئة مستند للقراءة الصوتية، ويتابعه فريق سند حتى يُحل.' },
];
const journeyIcons: Record<JourneyIcon, typeof Search> = { account: UserPlus, post: BriefcaseBusiness, filter: Filter, calendar: CalendarDays, decision: TrendingUp, compass: Compass, cv: FileUser, jobs: Search, track: ClipboardCheck, interview: HandMetal, support: LifeBuoy };
function Index() {
  const { signedIn, switchRole } = useSanad();
  const [track, setTrack] = useState<'company' | 'candidate'>('company');
  const steps = track === 'company' ? companyJourney : candidateJourney;
  const choices: { role: AccountRole; label: string; Icon: typeof Building2 }[] = [
    { role: 'company', label: 'لجهات التوظيف', Icon: Building2 },
    { role: 'candidate', label: 'للباحثين عن عمل', Icon: UserRound },
  ];
  return <div className="sanad-landing">
    <section id="home" className="landing-hero" aria-labelledby="hero-heading">
      <span className="landing-sweep landing-sweep--hero-top" aria-hidden="true" />
      <span className="landing-sweep landing-sweep--hero-bottom" aria-hidden="true" />
      <div className="landing-container landing-hero-inner">
        <div className="landing-hero-copy">
          <h1 id="hero-heading" className="landing-hero-title"><strong>سَند..</strong><span>حيث تلتقي الكفاءة بالفرصة.</span></h1>
          <span className="landing-accent-line" aria-hidden="true" />
          <p className="landing-hero-description">منصة توظيف ذكية تمكّن الصم والمكفوفين من الوصول إلى الفرص المناسبة لمهاراتهم، وتُمكّن جهات التوظيف من استقطاب كفاءاتهم، من التقديم حتى ما بعد التوظيف.</p>
          <div className="flex flex-wrap gap-3" role="group" aria-label="اختر نوع حسابك">{choices.map(({ role, label, Icon }) => <Button key={role} variant="landing" size="lg" asChild>{signedIn
            ? <Link to={role === 'company' ? '/company' : '/dashboard'} className="landing-start" onClick={() => switchRole(role)}><Icon aria-hidden="true" /><span>{label}</span><ArrowLeft aria-hidden="true" /></Link>
            : <Link to="/login" search={{ mode: 'signup', account: role }} className="landing-start"><Icon aria-hidden="true" /><span>{label}</span><ArrowLeft aria-hidden="true" /></Link>}</Button>)}</div>
        </div>
        <HeroPreview />
      </div>
    </section>
    <ScrollReveal className="landing-features" label="features-heading">
      <span className="landing-sweep landing-sweep--section-top" aria-hidden="true" />
      <span className="landing-sweep landing-sweep--section-bottom" aria-hidden="true" />
      <div className="landing-container" id="features">
        <div className="landing-section-heading reveal-heading"><span className="landing-accent-line" aria-hidden="true" /><h2 id="features-heading">مميزات سَند</h2></div>
        <div className="landing-feature-grid">{features.map(feature => <article className="landing-feature reveal-item" key={feature.kind}>
          <FeatureIllustration kind={feature.kind} />
          <h3>{feature.title}</h3>
          <span className="landing-accent-line" aria-hidden="true" />
          <p>{feature.text}</p>
          {feature.soon && <p className="landing-feature-soon">قريبًا</p>}
        </article>)}</div>
      </div>
    </ScrollReveal>
    <ScrollReveal className="landing-how" label="how-heading">
      <span className="landing-sweep landing-sweep--section-top" aria-hidden="true" />
      <span className="landing-sweep landing-sweep--section-bottom" aria-hidden="true" />
      <div className="landing-container" id="how-it-works">
        <div className="landing-section-heading reveal-heading"><h2 id="how-heading">كيف يعمل سَند؟</h2></div>
        <div className="landing-journey-tabs" role="tablist" aria-label="اختر المسار">{([{ id: 'company', label: 'لجهات التوظيف', Icon: Building2 }, { id: 'candidate', label: 'للباحثين عن عمل', Icon: UserRound }] as const).map(({ id, label, Icon }) => <button key={id} type="button" role="tab" aria-selected={track === id} className="landing-journey-tab" onClick={() => setTrack(id)}><Icon aria-hidden="true" />{label}</button>)}</div>
        <ol className="landing-journey" data-count={steps.length} role="tabpanel">{steps.map((step, index) => { const Icon = journeyIcons[step.icon]; return <li className="landing-step reveal-item" key={step.title}>
          <span className="landing-step-number" aria-hidden="true">{(index + 1).toLocaleString('ar-SA')}</span>
          <span className="landing-step-icon" aria-hidden="true"><Icon strokeWidth={1.6} /></span>
          <h3>{step.title}</h3><p>{step.detail}</p>
          {index < steps.length - 1 && <ArrowLeft className="landing-step-arrow" aria-hidden="true" />}
        </li>; })}</ol>
      </div>
    </ScrollReveal>
    <SiteFooter />
    <LandingDock />
  </div>;
}
