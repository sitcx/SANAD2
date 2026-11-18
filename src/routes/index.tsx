import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, BriefcaseBusiness, ClipboardCheck, FileUser, HandMetal, MoveUpRight, Search, Target } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SiteFooter } from '@/components/sanad-layout';
import { LandingDock } from '@/components/landing-dock';
import { FeatureIllustration } from '@/components/landing-illustrations';
import { ScrollReveal } from '@/components/scroll-reveal';
import { journeySteps } from '@/lib/sanad-data';
import { useSanad } from '@/lib/sanad-context';
import { pageHead } from '@/lib/page-head';
import gateway from '@/assets/sanad-gateway.jpg';

// A bundled gateway has no absolute public URL; hosting supplies the social preview.
export const Route = createFileRoute("/")({
  head: () => pageHead('سَند.. حيث تلتقي الكفاءة بالفرصة', 'منصة توظيف ذكية وتفاعلية مصممة خصيصًا للصم وضعاف السمع، تربط بين الكفاءات الوطنية وجهات التوظيف، وتدعم رحلتهم المهنية.'),
  component: Index,
});

type LandingFeature = { kind: 'jobs' | 'coach' | 'interview'; title: string; text: string; soon?: boolean };
const features: LandingFeature[] = [
  { kind: 'jobs', title: 'الوظائف المناسبة وخطة التهيئة', text: 'تحليل سيرتك، وترشيح وظائف تناسب مهاراتك، مع عرض التسهيلات المطلوبة لكل وظيفة.' },
  { kind: 'coach', title: 'التدريب الذكي على المقابلات', text: 'تدرّب على أسئلة مبسطة، واحصل على ملاحظات تساعدك على تحسين إجاباتك.', soon: true },
  { kind: 'interview', title: 'المقابلة الذكية', text: 'عرض أسئلة المقابلة نصيًا، وتحويل إجابات المرشح بلغة الإشارة إلى نص مكتوب، مع إتاحة مراجعة الإجابات وتعديلها واعتمادها قبل إرسالها.' },
];
const stepIcons = [FileUser, Search, BriefcaseBusiness, ClipboardCheck, Target, HandMetal];
function Index() {
  const { signedIn } = useSanad();
  return <div className="sanad-landing">
    <section id="home" className="landing-hero" aria-labelledby="hero-heading">
      <span className="landing-sweep landing-sweep--hero-top" aria-hidden="true" />
      <span className="landing-sweep landing-sweep--hero-bottom" aria-hidden="true" />
      <div className="landing-container landing-hero-inner">
        <div className="landing-hero-copy">
          <h1 id="hero-heading" className="landing-hero-title"><strong>سَند..</strong><span>حيث تلتقي الكفاءة بالفرصة.</span></h1>
          <span className="landing-accent-line" aria-hidden="true" />
          <p className="landing-hero-description">منصة توظيف ذكية وتفاعلية مصممة خصيصًا للصم وضعاف السمع، تربط بين الكفاءات الوطنية وجهات التوظيف، وتدعم رحلتهم المهنية من اكتشاف الفرص الوظيفية إلى اجتياز المقابلات.</p>
          <Button variant="landing" size="lg" asChild>{signedIn
            ? <Link to="/dashboard" className="landing-start"><span>ابدأ الآن</span><ArrowLeft aria-hidden="true" /></Link>
            : <Link to="/login" search={{ mode: 'signup' }} className="landing-start"><span>ابدأ الآن</span><ArrowLeft aria-hidden="true" /></Link>}</Button>
        </div>
        <div className="landing-gateway"><img src={gateway} width={1024} height={1024} alt="بوابة سَند المفتوحة، تجمع رمز لغة الإشارة وحقيبة العمل" fetchPriority="high" /></div>
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
        <div className="landing-section-heading reveal-heading"><p className="landing-eyebrow">خطوات العمل</p><h2 id="how-heading">كيف يعمل سَند؟</h2></div>
        <ol className="landing-journey">{journeySteps.map((step, index) => { const Icon = stepIcons[index]; return <li className="landing-step reveal-item" key={step.title}>
          <span className="landing-step-number" aria-hidden="true">{index + 1}</span>
          <span className="landing-step-icon" aria-hidden="true">{Icon && <Icon strokeWidth={1.6} />}{index === 1 && <span className="step-analysis-bars"><i /><i /><i /></span>}{index === 4 && <MoveUpRight className="step-target-arrow" />}{index === 5 && <span className="step-laptop-frame" />}</span>
          <h3>{step.title}</h3><p>{step.detail}</p>
          {index < journeySteps.length - 1 && <ArrowLeft className="landing-step-arrow" aria-hidden="true" />}
        </li>; })}</ol>
      </div>
    </ScrollReveal>
    <SiteFooter />
    <LandingDock />
  </div>;
}
