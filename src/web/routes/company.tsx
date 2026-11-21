import { createFileRoute } from '@tanstack/react-router';
import { AudioLines, BriefcaseBusiness, CalendarDays, Check, Filter, Hand, Plus, Send, UserCheck, Users, X } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { SpeakButton } from '@/components/speak-button';
import { candidatePool, companyActions, companyIndicators, rankCandidates, SELF_ID, selfCandidate, yearOptions, type CompanyJob, type PoolCandidate } from '@/lib/company';
import { useSanad } from '@/lib/sanad-context';
import { formatInterviewDate, jobs, statusLabels } from '@/lib/sanad-data';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/company')({ head: () => pageHead('لوحة الجهة', 'أضف الوظائف، واختر المرشحين حسب المهارات وسنوات الخبرة، وتابع مؤشرات التوظيف والاستمرار.'), component: Company });

const actionLabels = { nominate: 'ترشيح للمقابلة', schedule: 'تحديد موعد المقابلة', complete: 'محاكاة إتمام المقابلة', accept: 'قبول المرشح', reject: 'رفض' } as const;

function Company() {
  const state = useSanad();
  const allJobs: CompanyJob[] = [
    ...jobs.map(job => ({ id: job.id, title: job.title, skills: [...(state.jobSkills[job.id] ?? job.skills)], minYears: state.jobMinYears[job.id] ?? 1 })),
    ...state.companyJobs.map(job => ({ ...job, minYears: state.jobMinYears[job.id] ?? job.minYears })),
  ];
  const pool: PoolCandidate[] = [
    selfCandidate(state.candidateName, state.communicationMode, state.applications),
    ...candidatePool.map(candidate => ({ ...candidate, applications: state.poolApplications[candidate.id] ?? candidate.applications })),
  ];
  const [jobId, setJobId] = useState(allJobs[0]!.id);
  const job = allJobs.find(item => item.id === jobId) ?? allJobs[0]!;
  const [mustHave, setMustHave] = useState<string[]>([]);
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newSkills, setNewSkills] = useState('');
  const [newYears, setNewYears] = useState(1);
  const [formError, setFormError] = useState('');
  const [scheduling, setScheduling] = useState<string | null>(null);
  const [date, setDate] = useState('');
  const [message, setMessage] = useState('');

  if (state.role !== 'company') return <Workspace><PageTitle title="لوحة الجهة" subtitle="هذه اللوحة لحسابات جهات التوظيف." /><section className="workspace-section"><BriefcaseBusiness className="size-9 text-primary" /><p className="text-sm text-muted-foreground mt-4">سجّل الدخول بحساب جهة توظيف، أو بدّل الحساب في هذه التجربة.</p><Button className="mt-5" onClick={() => state.switchRole('company')}>التبديل إلى حساب الجهة (تجربة)</Button></section></Workspace>;

  const overall = companyIndicators(allJobs, pool);
  const ranked = rankCandidates(job, pool, { minYears: job.minYears, mustHave });
  const tiles = [
    { label: 'المتقدمون', value: overall.applicants.toLocaleString('ar-SA'), Icon: Users },
    { label: 'متوسط التوافق', value: `${overall.averageMatch.toLocaleString('ar-SA')}٪`, Icon: Check },
    { label: 'وصلوا للمقابلة', value: `${overall.interviewRate.toLocaleString('ar-SA')}٪`, Icon: CalendarDays },
    { label: 'توظفوا', value: overall.hired.toLocaleString('ar-SA'), Icon: UserCheck },
    { label: 'نسبة الاستمرار', value: overall.retention === null ? '—' : `${overall.retention.toLocaleString('ar-SA')}٪`, Icon: BriefcaseBusiness },
  ];

  function selectJob(id: string) { setJobId(id); setMustHave([]); setScheduling(null); setMessage(''); }
  function addJob(event: FormEvent) {
    event.preventDefault();
    const error = state.addCompanyJob(newTitle, newSkills.split(/[،,]/), newYears);
    if (error) return setFormError(error);
    setNewTitle(''); setNewSkills(''); setNewYears(1); setFormError(''); setAdding(false);
  }
  function act(candidateId: string, action: keyof typeof actionLabels) {
    setMessage('');
    if (action === 'schedule') { setScheduling(candidateId); setDate(''); return; }
    const next = { nominate: 'nominated', complete: 'completed', accept: 'accepted', reject: 'rejected' } as const;
    state.companyUpdateCandidate(candidateId, job.id, next[action]);
  }
  function confirmSchedule(candidateId: string) {
    if (!date) return setMessage('اختر موعد المقابلة.');
    const error = state.companySchedule(candidateId, job.id, `${date}:00+03:00`);
    if (error) return setMessage(error);
    setScheduling(null); setMessage('تم تحديد موعد المقابلة، ووصل الموعد إلى المرشح.');
  }

  return <Workspace><PageTitle title="لوحة الجهة" subtitle={`${state.companyName}: اختر المرشح المناسب حسب احتياجك.`} />
    <section aria-label="مؤشرات التوظيف" className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">{tiles.map(({ label, value, Icon }) => <div key={label} className="surface p-4 rounded-xl"><p className="text-xs text-muted-foreground flex items-center gap-1.5"><Icon className="size-4 text-primary" />{label}</p><p className="text-2xl font-semibold mt-2 tabular-nums">{value}</p></div>)}</section>

    <section className="workspace-section" aria-labelledby="company-jobs">
      <div className="section-title"><h2 id="company-jobs"><BriefcaseBusiness />وظائف الجهة</h2><Button variant="outline" onClick={() => setAdding(!adding)}>{adding ? <X /> : <Plus />}{adding ? 'إلغاء' : 'إضافة وظيفة'}</Button></div>
      {adding && <form onSubmit={addJob} noValidate className="grid gap-4 sm:grid-cols-3 mb-6 border-b border-border pb-6">
        <div><label htmlFor="job-title" className="block text-sm font-medium mb-2">المسمى الوظيفي</label><Input id="job-title" value={newTitle} onChange={event => setNewTitle(event.target.value)} placeholder="مثال: مدخل بيانات" /></div>
        <div><label htmlFor="job-skills" className="block text-sm font-medium mb-2">المهارات المطلوبة (افصل بفاصلة)</label><Input id="job-skills" value={newSkills} onChange={event => setNewSkills(event.target.value)} placeholder="Excel، تحليل البيانات" /></div>
        <div><label className="block text-sm font-medium mb-2" id="job-years-label">سنوات الخبرة المطلوبة</label><Select value={String(newYears)} onValueChange={value => setNewYears(Number(value))} dir="rtl"><SelectTrigger aria-labelledby="job-years-label"><SelectValue /></SelectTrigger><SelectContent>{yearOptions.map(option => <SelectItem key={option.value} value={String(option.value)}>{option.label}</SelectItem>)}</SelectContent></Select></div>
        {formError && <p role="alert" className="text-sm text-destructive sm:col-span-3">{formError}</p>}
        <div className="sm:col-span-3"><Button type="submit"><Send />نشر الوظيفة</Button></div>
      </form>}
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="اختر الوظيفة">{allJobs.map(item => <Button key={item.id} role="tab" aria-selected={item.id === job.id} variant={item.id === job.id ? 'secondary' : 'outline'} onClick={() => selectJob(item.id)}>{item.title}</Button>)}</div>
    </section>

    <section className="workspace-section" aria-labelledby="company-filter">
      <div className="section-title"><h2 id="company-filter"><Filter />احتياج الجهة في «{job.title}»</h2></div>
      <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_16rem]">
        <fieldset><legend className="text-sm font-medium mb-3">مهارات يجب أن تتوفر في المرشح</legend><div className="flex flex-wrap gap-2">{job.skills.map(skill => { const on = mustHave.includes(skill); return <Button key={skill} type="button" size="sm" variant={on ? 'secondary' : 'outline'} aria-pressed={on} onClick={() => setMustHave(current => on ? current.filter(item => item !== skill) : [...current, skill])}>{on && <Check />}{skill}</Button>; })}</div><p className="text-xs text-muted-foreground mt-2">نسبة التوافق تُحسب من كل المهارات المطلوبة؛ المهارات المختارة هنا شرط لظهور المرشح.</p></fieldset>
        <div><label className="block text-sm font-medium mb-3" id="filter-years-label">سنوات الخبرة</label><Select value={String(job.minYears)} onValueChange={value => state.setJobMinYears(job.id, Number(value))} dir="rtl"><SelectTrigger aria-labelledby="filter-years-label"><SelectValue /></SelectTrigger><SelectContent>{yearOptions.map(option => <SelectItem key={option.value} value={String(option.value)}>{option.label}</SelectItem>)}</SelectContent></Select></div>
      </div>
    </section>

    <section className="workspace-section" aria-labelledby="company-candidates">
      <div className="section-title"><h2 id="company-candidates"><Users />المرشحون المطابقون</h2><span className="text-sm text-muted-foreground">{ranked.length.toLocaleString('ar-SA')} مرشح</span></div>
      {job.custom && !pool.some(candidate => candidate.applications[job.id]) && <p className="text-sm text-muted-foreground mb-4">لا يوجد متقدمون بعد؛ هؤلاء مرشحون من سند تتوافق مهاراتهم مع الوظيفة.</p>}
      {message && <p role="status" className="text-sm text-primary mb-4">{message}</p>}
      {ranked.length === 0 ? <p className="text-sm text-muted-foreground">لا يوجد مرشحون بهذه الفلترة. خفّف شروط المهارات أو سنوات الخبرة.</p> : <div className="space-y-4">{ranked.map(({ candidate, status, match }) => {
        const self = candidate.id === SELF_ID;
        const actions = companyActions(status).filter(action => !(self && action === 'complete'));
        const schedule = self ? state.schedules[job.id] : state.poolSchedules[`${candidate.id}:${job.id}`];
        const owned = new Set(candidate.skills.map(skill => skill.toLowerCase()));
        return <article key={candidate.id} className="tracking-row" aria-label={`المرشح ${candidate.name}`}>
          <div className="flex flex-wrap justify-between items-start gap-3">
            <div><h3 className="font-semibold">{candidate.name}{self && <span className="text-xs text-muted-foreground font-normal"> · المرشح الحالي في التجربة</span>}</h3>
              <p className="text-sm text-muted-foreground mt-1 flex flex-wrap items-center gap-3"><span className="flex items-center gap-1">{candidate.mode === 'sign' ? <Hand className="size-4" /> : <AudioLines className="size-4" />}{candidate.mode === 'sign' ? 'أصم · المقابلة بمترجم إشارة' : 'كفيف · المقابلة صوتية'}</span><span>{candidate.years.toLocaleString('ar-SA')} {candidate.years > 2 ? 'سنوات' : candidate.years === 2 ? 'سنتان' : 'سنة'} خبرة</span></p></div>
            <div className="flex items-center gap-2"><SpeakButton label={`المرشح ${candidate.name}`} text={`${candidate.name}، توافق ${match} بالمئة، خبرة ${candidate.years} سنوات. الحالة: ${statusLabels[status]}.`} /><span className="status-label whitespace-nowrap"><Check className="size-4" />{match.toLocaleString('ar-SA')}٪ توافق</span><span className="status-label" data-status={status}>{statusLabels[status]}</span></div>
          </div>
          <div className="flex flex-wrap gap-2 mt-4">{candidate.skills.map(skill => <span key={skill} className="skill-tag" dir="auto" data-match={job.skills.some(required => required.toLowerCase() === skill.toLowerCase())}>{skill}</span>)}{job.skills.filter(skill => !owned.has(skill.toLowerCase())).map(skill => <span key={skill} className="skill-tag opacity-50 line-through" dir="auto" title="مهارة مطلوبة غير متوفرة">{skill}</span>)}</div>
          {schedule && ['scheduled', 'nominated'].includes(status) && <p className="text-sm mt-3 flex items-center gap-2"><CalendarDays className="size-4 text-primary" />موعد المقابلة: {formatInterviewDate(schedule)}</p>}
          {self && status === 'scheduled' && <p className="text-xs text-muted-foreground mt-2">بانتظار دخول المرشح إلى المقابلة في موعدها.</p>}
          {status === 'accepted' && <p className="text-xs text-muted-foreground mt-2">بانتظار قبول المرشح للعرض الوظيفي.</p>}
          {scheduling === candidate.id ? <div className="flex flex-wrap items-end gap-3 mt-4"><div><label htmlFor={`date-${candidate.id}`} className="block text-sm font-medium mb-2">موعد المقابلة · بتوقيت الرياض</label><Input id={`date-${candidate.id}`} type="datetime-local" dir="ltr" value={date} onChange={event => setDate(event.target.value)} /></div><Button onClick={() => confirmSchedule(candidate.id)}><Check />تأكيد الموعد</Button><Button variant="ghost" onClick={() => setScheduling(null)}>إلغاء</Button></div>
            : actions.length > 0 && <div className="flex flex-wrap gap-2 mt-4">{actions.map(action => <Button key={action} variant={action === 'reject' ? 'outline' : 'default'} onClick={() => act(candidate.id, action)}>{actionLabels[action]}</Button>)}</div>}
        </article>;
      })}</div>}
    </section>
  </Workspace>;
}
