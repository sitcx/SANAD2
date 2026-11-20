import { Link } from '@tanstack/react-router';
import { ArrowLeft, BriefcaseBusiness, Building2, Check, MapPin, Send, Target } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getJobMatch, statusLabels, type Job } from '@/lib/sanad-data';
import { useSanad } from '@/lib/sanad-context';
import { getTrainingReadiness } from '@/lib/training-readiness';

export function JobCard({ job }: { job: Job }) {
  const state = useSanad();
  const match = getJobMatch(job, state.cvStatus);
  const trainingReadiness = getTrainingReadiness(state.trainingProgress[job.id]);
  const status = state.applications[job.id] ?? 'available';
  return <article className="surface job-card">
    <div className="flex flex-wrap justify-between gap-3">
      <div className="flex min-w-0 items-center gap-3"><span className="job-mark" aria-hidden="true"><Building2 /></span><div className="min-w-0"><h3 className="font-semibold text-lg">{job.title}</h3><p className="text-sm text-muted-foreground">{job.company}</p></div></div>
      <div className="flex flex-wrap items-center gap-2 self-start">
        {match !== null && <span className="status-label whitespace-nowrap"><Check className="size-4 shrink-0" />{match.toLocaleString('ar-SA')}٪ توافق</span>}
        <span className="status-label bg-muted text-muted-foreground whitespace-nowrap" title="نسبة أسئلة التدريب المكتملة لهذه الوظيفة، وليست تقييمًا لجودة الإجابات"><Target className="size-4 shrink-0" />{trainingReadiness.toLocaleString('ar-SA')}٪ جاهزية التدريب</span>
      </div>
    </div>
    <p className="text-sm text-muted-foreground mt-4">{job.description}</p>
    {match !== null && <p className="text-xs text-primary mt-2">{job.id === 'analyst' ? 'لأن مهاراتك في Excel وSQL تتوافق مع متطلبات الدور.' : job.id === 'support' ? 'لأن التواصل الكتابي أساس العمل، وهو من نقاط قوتك.' : 'لأن خبرتك في التصميم تساعدك على بناء تجارب واضحة.'}</p>}
    <div className="flex flex-wrap gap-2 mt-4">{(state.jobSkills[job.id] ?? job.skills).map(skill => <span key={skill} className="skill-tag" dir="auto">{skill}</span>)}</div>
    <p className="mt-4 text-xs font-medium text-primary">{statusLabels[status]}</p>
    <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] items-center border-t border-border pt-4 mt-4">
      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground"><span className="flex items-center gap-1.5"><MapPin className="size-4" />{job.location}</span><span className="flex items-center gap-1.5"><BriefcaseBusiness className="size-4" />{job.mode}</span><span>{job.salary}</span></div>
      <div className="flex flex-wrap gap-2"><Button asChild variant="outline"><Link to="/jobs/$jobId" params={{ jobId: job.id }} aria-label={`عرض الوظيفة: ${job.title}`}>عرض الوظيفة<ArrowLeft /></Link></Button>{status === 'available' && <Button disabled={state.cvStatus !== 'analysed'} onClick={() => state.applyToJob(job.id)}><Send />التقديم على الوظيفة</Button>}</div>
    </div>
    {status === 'available' && <p className="text-xs text-muted-foreground mt-3">{state.cvStatus !== 'analysed' ? 'أكمل تحليل سيرتك الذاتية في لوحة التحكم قبل التقديم. ' : ''}تقديم تجريبي في الجلسة الحالية؛ لا يُرسل إلى شركة حقيقية.</p>}
  </article>;
}