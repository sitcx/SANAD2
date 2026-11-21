import { Link } from '@tanstack/react-router';
import { ArrowLeft, CalendarClock, ClipboardList, FileUp, Gift, Hourglass, LifeBuoy, Search, Video } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SpeakButton } from '@/components/speak-button';
import { useSanad } from '@/lib/sanad-context';
import { nextStep, type NextStepKind } from '@/lib/next-step';

const icons: Record<NextStepKind, typeof Search> = {
  support: LifeBuoy, offer: Gift, 'interview-now': Video, 'interview-soon': CalendarClock,
  decision: Hourglass, review: ClipboardList, cv: FileUp, apply: Search,
};

/** Dashboard card: the candidate's next action, based on their CV and applications. */
export function NextStepCard() {
  const state = useSanad();
  const step = nextStep({ cvName: state.cvName, cvStatus: state.cvStatus, applications: state.applications, schedules: state.schedules, now: state.now });
  const Icon = icons[step.kind];
  const select = () => { if (step.jobId) state.selectJob(step.jobId); };
  return <section className="workspace-section next-step-card" aria-labelledby="next-step-title" data-kind={step.kind}>
    <div className="section-title"><h2 id="next-step-title"><Icon aria-hidden="true" />خطوتك القادمة</h2><SpeakButton label="خطوتك القادمة" text={`${step.title}. ${step.text}`} /></div>
    <div className="next-step-body">
      <h3 className="next-step-heading">{step.title}</h3>
      <p className="next-step-text">{step.text}</p>
      <Button asChild className="mt-5">{step.kind === 'cv'
        ? <a href="#cv-title">{step.action}<ArrowLeft /></a>
        : step.to === '/interview' ? <Link to="/interview" search={step.preview ? { preview: true } : {}} onClick={select}>{step.action}<ArrowLeft /></Link>
        : <Link to={step.to}>{step.action}<ArrowLeft /></Link>}</Button>
    </div>
  </section>;
}
