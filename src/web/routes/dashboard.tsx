import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, ArrowRight, Compass, LifeBuoy, X } from 'lucide-react';
import { careerTrackLabel } from '@/lib/career-discovery';
import { Button } from '@/components/ui/button';
import { SpeakButton } from '@/components/speak-button';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { NextStepCard } from '@/components/next-step-card';
import { InterviewCalendar } from '@/components/interview-calendar';
import { AgentMatches, CvAgentCard } from '@/components/cv-agent';
import { useCvAgent } from '@/hooks/use-cv-agent';
import { useSanad } from '@/lib/sanad-context';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/dashboard')({ head: () => pageHead('لوحة التحكم', 'مهارة مهنية مفيدة مع مثال عملي، تقويم مواعيدك، سيرتك الذاتية والوظائف المناسبة لك في مساحة واحدة.'), component: Dashboard });
function Dashboard() {
  const state = useSanad();
  const cvAgent = useCvAgent();
  const guest = !state.signedIn;
  return <Workspace><Button asChild variant="ghost" className="mb-2 px-2"><Link to="/" aria-label="العودة إلى الرئيسية"><ArrowRight />العودة إلى الرئيسية</Link></Button><PageTitle title="لوحة التحكم" subtitle={`مرحبًا ${state.candidateName}، لنجهّز خطوتك القادمة.`} />
    {!guest && !state.careerDecided && <section className="workspace-section" aria-labelledby="discover-title"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 id="discover-title" className="text-lg font-semibold flex items-center gap-2"><Compass className="text-primary" />تريد أن تكتشف مسارك المهني؟</h2><p className="text-sm text-muted-foreground mt-2">خمسة أسئلة عامة عن ميولك تقترح عليك المسار والوظائف المناسبة. الخطوة اختيارية.</p></div><div className="flex flex-wrap gap-2"><SpeakButton label="اكتشف مسارك المهني" text="تريد أن تكتشف مسارك المهني؟ خمسة أسئلة عامة عن ميولك تقترح عليك المسار والوظائف المناسبة. الخطوة اختيارية. اضغط ابدأ الاكتشاف، أو أعرف مساري للتخطي." /><Button asChild><Link to="/discover">ابدأ الاكتشاف<ArrowLeft /></Link></Button><Button variant="ghost" onClick={state.skipCareerDiscovery}><X />أعرف مساري</Button></div></div></section>}
    {!guest && state.careerTrack && <p className="text-sm text-muted-foreground mb-5 flex items-center gap-2"><Compass className="size-4 text-primary" />مسارك المهني المقترح: <strong className="text-foreground">{careerTrackLabel(state.careerTrack)}</strong></p>}
    {!guest && Object.values(state.applications).includes('hired') && <section className="workspace-section" aria-labelledby="hired-title"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 id="hired-title" className="text-lg font-semibold flex items-center gap-2"><LifeBuoy className="text-primary" />مبارك وظيفتك الجديدة</h2><p className="text-sm text-muted-foreground mt-2">سند معك بعد التوظيف. إذا واجهت أي صعوبة في عملك، ارفع طلب دعم ونتابعه حتى يُحل.</p></div><div className="flex gap-2"><SpeakButton label="مبارك وظيفتك الجديدة" text="مبارك وظيفتك الجديدة. سند معك بعد التوظيف. إذا واجهت أي صعوبة في عملك، ارفع طلب دعم ونتابعه حتى يُحل." /><Button asChild><Link to="/support">دعم سند<ArrowLeft /></Link></Button></div></div></section>}
    <div className="dashboard-overview">
      <NextStepCard />
      <CvAgentCard agent={cvAgent} />
      <InterviewCalendar empty={guest} />
    </div>
    <AgentMatches agent={cvAgent} />
  </Workspace>;
}
