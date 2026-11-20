import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, ArrowRight, BriefcaseBusiness, Building2, CalendarDays, Check, ClipboardCheck, Clock3, Mail, MapPin, MessageSquareText, Target, Video } from 'lucide-react';
import { useState } from 'react';
import { EmployerControls } from '@/components/employer-controls';
import { JobCommunicationPreferences } from '@/components/job-communication-preferences';
import { Button } from '@/components/ui/button';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { accommodationItems, canJoinInterview, formatInterviewDate, getJobMatch, jobs, nextSteps, remainingTime, statusLabels } from '@/lib/sanad-data';
import { useSanad } from '@/lib/sanad-context';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/jobs_/$jobId')({
  head: ({ params }) => {
    const job = jobs.find(item => item.id === params.jobId);
    return pageHead(job ? `${job.title} — ${job.company}` : 'الوظيفة غير موجودة', job ? `تفاصيل وظيفة ${job.title} وخطة التهيئة والتقديم لدى ${job.company}.` : 'عد إلى الوظائف لاستكشاف الفرص المتاحة في سَند.');
  },
  component: JobDetail,
});
const planIcons = [MessageSquareText, Clock3, Video, Mail];
function JobDetail() {
  const { jobId } = Route.useParams();
  const state = useSanad();
  const [employer, setEmployer] = useState(false);
  const job = jobs.find(item => item.id === jobId);
  if (!job) return <Workspace><PageTitle title="الوظيفة غير موجودة" subtitle="يمكنك العودة لاستكشاف الفرص المتاحة." /><Button asChild><Link to="/jobs">العودة إلى الوظائف<ArrowRight /></Link></Button></Workspace>;
  const status = state.applications[job.id] ?? 'available';
  const match = getJobMatch(job, state.cvStatus);
  const allowed = canJoinInterview(status, (state.schedules[job.id] ?? ''), state.now);
  return <Workspace>
    <Button asChild variant="link" className="px-0 mb-4"><Link to="/jobs"><ArrowRight />الوظائف</Link></Button>
    <div className="flex flex-wrap gap-2 mb-5" role="group" aria-label="عرض الوظيفة"><Button variant={!employer ? 'secondary' : 'ghost'} aria-pressed={!employer} onClick={() => setEmployer(false)}>المرشح</Button><Button variant={employer ? 'secondary' : 'ghost'} aria-pressed={employer} onClick={() => setEmployer(true)}>الشركة · محاكاة</Button></div><PageTitle title={job.title} subtitle={job.company} action={<span className="job-mark" aria-hidden="true"><Building2 /></span>} />
    <div className="flex flex-wrap items-center gap-3 mb-7"><span className="status-label">{statusLabels[status]}</span>{match !== null && <span className="text-sm text-primary">{match.toLocaleString('ar-SA')}٪ توافق مع سيرتك</span>}</div>
    <section className="workspace-section"><div className="section-title"><h2><BriefcaseBusiness />تفاصيل الوظيفة</h2></div><p className="text-sm leading-loose">{job.description}</p><div className="flex flex-wrap gap-5 text-sm text-muted-foreground mt-4"><span className="flex items-center gap-2"><MapPin className="size-5" />{job.location}</span><span>{job.mode}</span><span>{job.salary}</span></div><h3 className="font-semibold text-sm mt-6">المهارات المطلوبة</h3><div className="flex flex-wrap gap-2 mt-3">{(state.jobSkills[job.id] ?? job.skills).map(skill => <span className="skill-tag" key={skill}>{skill}</span>)}</div></section>
    <section className="workspace-section"><div className="section-title"><h2><ClipboardCheck />خطة التهيئة</h2></div><p className="text-sm font-semibold text-primary mb-3">{match !== null ? `مناسبة لك بنسبة ${match.toLocaleString('ar-SA')}٪` : 'أكمل تحليل سيرتك لعرض نسبة التوافق.'}</p><p className="text-sm text-muted-foreground mb-5">تسهيلات التقديم والمقابلة والعمل لدى {job.company}.</p><ul className="grid gap-5 sm:grid-cols-2">{accommodationItems.map((item, index) => { const Icon = planIcons[index]; return <li className="flex items-start gap-3" key={item.id}>{Icon && <Icon className="size-6 text-primary shrink-0 mt-1" />}<div><h3 className="font-semibold text-sm">{item.title}</h3><p className="text-sm text-muted-foreground mt-1 leading-loose">{item.detail}</p></div></li>; })}</ul>
      <JobCommunicationPreferences jobId={job.id} />
    </section>
    <section className="workspace-section" aria-live="polite">
      {status === 'available' && <><div className="section-title"><h2><BriefcaseBusiness />التقديم على الوظيفة</h2></div><p className="text-sm text-muted-foreground mb-5">تُرفق سيرتك وتفضيلات التواصل بطلبك التجريبي؛ لا يُرسل إلى شركة حقيقية.</p>{state.cvStatus !== 'analysed' && <p className="text-sm text-primary mb-4">أكمل تحليل سيرتك الذاتية في لوحة التحكم قبل التقديم.</p>}<Button disabled={state.cvStatus !== 'analysed'} onClick={() => state.applyToJob(job.id)}>التقديم على الوظيفة<ArrowLeft /></Button></>}
      {(status === 'applied' || status === 'reviewing') && <><div className="section-title"><h2><Check />تم تقديم طلبك</h2></div><p className="text-sm text-muted-foreground mb-5">بانتظار رد الشركة. يمكنك تجربة خطوة الترشيح التالية دون إرسال فعلي.</p><Button variant="outline" onClick={() => state.nominateJob(job.id)}><CalendarDays />محاكاة الترشيح للمقابلة</Button></>}
      {['nominated', 'scheduled'].includes(status) && <><div className="section-title"><h2><CalendarDays />تم ترشيحك للمقابلة</h2></div><p className="text-sm mb-2">{formatInterviewDate((state.schedules[job.id] ?? ''))}</p><p className="text-xs text-muted-foreground mb-5">بتوقيت الرياض · مقابلة تجريبية · تفضيلاتك وخطة التهيئة أعلاه متاحة للمقابلة.</p><div className="flex flex-wrap gap-3">{allowed ? <Button asChild><Link to="/interview" onClick={() => state.selectJob(job.id)}><Video />الدخول للمقابلة<ArrowLeft /></Link></Button> : <Button disabled><Clock3 />الدخول للمقابلة</Button>}</div>{!allowed && <p className="text-xs text-muted-foreground mt-3">{remainingTime(state.schedules[job.id] ?? '', state.now)}</p>}</>}
      {['completed', 'accepted', 'rejected', 'withdrawn'].includes(status) && <><h2 className="font-semibold text-lg">{statusLabels[status]}</h2><p className="text-sm text-muted-foreground mt-3">{nextSteps[status]}</p><Button asChild variant="outline" className="mt-5"><Link to="/applications">تتبع تقديماتي<ArrowLeft /></Link></Button></>}
    </section>
    <section className="workspace-section"><div className="section-title"><h2><Video />تجربة التدريب والمقابلة</h2></div><p className="text-sm text-muted-foreground mb-4">التجربة متاحة الآن دون ترشيح أو انتظار الموعد؛ لا تغيّر حالة الطلب ولا تُرسل إلى الشركة.</p><div className="flex flex-wrap gap-3"><Button asChild variant="outline"><Link to="/coach" onClick={() => state.selectJob(job.id)}><Target />التدريب على المقابلة</Link></Button><Button asChild><Link to="/interview" search={{ preview: true }} onClick={() => state.selectJob(job.id)}><Video />تجربة المقابلة والكاميرا</Link></Button></div></section>
    {employer && <EmployerControls job={job} />}
  </Workspace>;
}