import { createFileRoute } from '@tanstack/react-router';
import { AudioLines, BriefcaseBusiness, CalendarDays, Check, Filter, Hand, LoaderCircle, MapPin, Plus, RefreshCw, RotateCcw, Send, TrendingUp, UserCheck, Users, WifiOff, X } from 'lucide-react';
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { SpeakButton } from '@/components/speak-button';
import { companyActions, yearOptions } from '@/lib/company';
import { ApiError, companyApi, SELF_TALENT_ID, type Indicators, type Posting, type RankedTalent } from '@/lib/company-api';
import { useSanad } from '@/lib/sanad-context';
import { formatInterviewDate, statusLabels, type ApplicationStatus } from '@/lib/sanad-data';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/company')({ head: () => pageHead('لوحة الجهة', 'أضف الوظائف، واختر المرشحين حسب المهارات وسنوات الخبرة، وتابع مؤشرات التوظيف والاستمرار.'), component: Company });

const actionLabels = { nominate: 'ترشيح للمقابلة', schedule: 'تحديد موعد المقابلة', complete: 'تسجيل إتمام المقابلة', accept: 'قبول المرشح', reject: 'رفض' } as const;
const nextStatus = { nominate: 'nominated', complete: 'completed', accept: 'accepted', reject: 'rejected' } as const satisfies Record<string, ApplicationStatus>;
const pct = (value: number) => `${value.toLocaleString('ar-SA')}٪`;
const yearsLabel = (years: number) => years === 0 ? 'بدون خبرة' : years === 1 ? 'سنة خبرة' : years === 2 ? 'سنتان خبرة' : `${years.toLocaleString('ar-SA')} ${years <= 10 ? 'سنوات' : 'سنة'} خبرة`;

function Company() {
  const state = useSanad();
  const [postings, setPostings] = useState<Posting[]>([]);
  const [indicators, setIndicators] = useState<Indicators | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [mustHave, setMustHave] = useState<string[]>([]);
  const [candidates, setCandidates] = useState<RankedTalent[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ title: '', skills: '', years: 1 });
  const [formError, setFormError] = useState('');
  const [scheduling, setScheduling] = useState<string | null>(null);
  const [date, setDate] = useState('');
  const [confirmReset, setConfirmReset] = useState(false);
  const job = postings.find(item => item.id === jobId) ?? postings[0] ?? null;

  const loadOverview = useCallback(async () => {
    const [jobs, overall] = await Promise.all([companyApi.jobs(), companyApi.indicators()]);
    setPostings(jobs); setIndicators(overall);
    setJobId(current => current && jobs.some(item => item.id === current) ? current : jobs[0]?.id ?? null);
  }, []);
  const loadCandidates = useCallback(async (posting: Posting, skills: string[]) => {
    setCandidates(await companyApi.candidates(posting.id, posting.min_years, skills));
  }, []);

  useEffect(() => {
    if (state.role !== 'company') return;
    setLoading(true);
    loadOverview().then(() => setError('')).catch((err: unknown) => setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع.')).finally(() => setLoading(false));
  }, [state.role, loadOverview]);
  useEffect(() => {
    if (!job) return;
    setCandidates(null);
    loadCandidates(job, mustHave).catch((err: unknown) => setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع.'));
  }, [job?.id, job?.min_years, mustHave, loadCandidates]); // eslint-disable-line react-hooks/exhaustive-deps

  if (state.role !== 'company') return <Workspace><PageTitle title="لوحة الجهة" subtitle="هذه اللوحة لحسابات جهات التوظيف." /><section className="workspace-section"><BriefcaseBusiness className="size-9 text-primary" /><p className="text-sm text-muted-foreground mt-4">ادخل بحساب جهة التوظيف لعرض الوظائف والمرشحين ومؤشرات التوظيف.</p><Button className="mt-5" onClick={() => state.signedIn ? state.switchRole('company') : state.signIn(state.companyName, '', undefined, 'company')}>الدخول كجهة توظيف</Button></section></Workspace>;

  /** Runs a change on the server, then reloads everything so the numbers stay real. */
  async function run(key: string, change: () => Promise<unknown>, done?: string) {
    setBusy(key); setMessage('');
    try {
      await change();
      await loadOverview();
      if (job) await loadCandidates(job, mustHave);
      setError(''); if (done) setMessage(done);
      return true;
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع.');
      return false;
    } finally { setBusy(null); }
  }
  function act(item: RankedTalent, action: keyof typeof actionLabels) {
    if (!job) return;
    if (action === 'schedule') { setScheduling(item.talent.id); setDate(''); return; }
    const status = nextStatus[action];
    void run(`${item.talent.id}:${action}`, async () => {
      await companyApi.setStatus(job.id, item.talent.id, status);
      if (item.talent.id === SELF_TALENT_ID) state.syncSelfApplication(job.id, status);
    }, `${item.talent.name}: ${statusLabels[status]}.`);
  }
  function confirmSchedule(item: RankedTalent) {
    if (!job) return;
    if (!date) return setMessage('اختر موعد المقابلة.');
    void run(`${item.talent.id}:schedule`, async () => {
      const { interview_at } = await companyApi.schedule(job.id, item.talent.id, `${date}:00+03:00`);
      if (item.talent.id === SELF_TALENT_ID) state.syncSelfApplication(job.id, 'scheduled', interview_at);
    }, `تم تحديد موعد مقابلة ${item.talent.name}، ووصل الموعد إلى المرشح.`).then(ok => { if (ok) setScheduling(null); });
  }
  async function addJob(event: FormEvent) {
    event.preventDefault();
    setFormError('');
    try {
      const created = await companyApi.createJob({ title: form.title, skills: form.skills.split(/[،,]/), min_years: form.years });
      await loadOverview();
      setJobId(created.id); setMustHave([]); setAdding(false); setForm({ title: '', skills: '', years: 1 });
      setMessage(`نُشرت وظيفة «${created.title}».`);
    } catch (err) { setFormError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع.'); }
  }
  function selectJob(id: string) { setJobId(id); setMustHave([]); setScheduling(null); setMessage(''); }

  const tiles = indicators ? [
    { label: 'الوظائف المنشورة', value: indicators.postings.toLocaleString('ar-SA'), Icon: BriefcaseBusiness },
    { label: 'المتقدمون', value: indicators.applicants.toLocaleString('ar-SA'), Icon: Users },
    { label: 'متوسط التوافق', value: pct(indicators.average_match), Icon: Check },
    { label: 'وصلوا للمقابلة', value: pct(indicators.interview_rate), Icon: CalendarDays },
    { label: 'توظفوا', value: indicators.hired.toLocaleString('ar-SA'), Icon: UserCheck },
    { label: 'نسبة الاستمرار', value: indicators.retention === null ? '—' : pct(indicators.retention), Icon: TrendingUp },
  ] : [];
  const deaf = indicators?.by_mode.sign.applicants ?? 0;
  const blind = indicators?.by_mode.voice.applicants ?? 0;

  return <Workspace>
    <PageTitle title="لوحة الجهة" subtitle={`${state.companyName}: اختر المرشح المناسب حسب احتياجك.`} action={<div className="flex flex-wrap gap-2"><Button onClick={() => setAdding(true)}><Plus />وظيفة جديدة</Button><Button variant="outline" size="icon" aria-label="تحديث البيانات" title="تحديث البيانات" disabled={busy !== null} onClick={() => void run('refresh', async () => undefined)}><RefreshCw className={busy === 'refresh' ? 'animate-spin' : ''} /></Button></div>} />

    {error && <section className="workspace-section company-offline" role="alert"><WifiOff className="size-8 text-destructive" /><div><h2 className="font-semibold">الخادم غير متصل</h2><p className="text-sm text-muted-foreground mt-1">{error}</p></div><Button variant="outline" onClick={() => { setLoading(true); loadOverview().then(() => setError('')).catch((err: unknown) => setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع.')).finally(() => setLoading(false)); }}><RotateCcw />إعادة المحاولة</Button></section>}
    {loading && !error && <p className="flex items-center gap-2 text-sm text-muted-foreground mb-6" role="status"><LoaderCircle className="animate-spin size-4" />جارٍ تحميل بيانات الجهة…</p>}

    {indicators && <>
      <section id="company-kpis" aria-label="مؤشرات التوظيف" className="company-kpis">{tiles.map(({ label, value, Icon }) => <div key={label} className="company-kpi"><span className="company-kpi-icon"><Icon aria-hidden="true" /></span><p className="company-kpi-value">{value}</p><p className="company-kpi-label">{label}</p></div>)}</section>
      <div className="company-mode-split" aria-label="توزيع المتقدمين"><div className="flex justify-between text-xs text-muted-foreground mb-2"><span className="flex items-center gap-1"><Hand className="size-4" />الصم: {deaf.toLocaleString('ar-SA')} متقدم · {indicators.by_mode.sign.hired.toLocaleString('ar-SA')} توظفوا</span><span className="flex items-center gap-1"><AudioLines className="size-4" />المكفوفون: {blind.toLocaleString('ar-SA')} متقدم · {indicators.by_mode.voice.hired.toLocaleString('ar-SA')} توظفوا</span></div><div className="company-mode-bar"><span style={{ width: `${deaf + blind ? deaf / (deaf + blind) * 100 : 50}%` }} /></div></div>
    </>}

    {postings.length > 0 && job && <div className="company-layout">
      <aside id="company-jobs" className="company-jobs" aria-label="وظائف الجهة">
        <h2 className="company-jobs-title"><BriefcaseBusiness className="size-5" />وظائف الجهة <span>{postings.length.toLocaleString('ar-SA')}</span></h2>
        <div className="company-jobs-list" role="tablist" aria-orientation="vertical">{postings.map(item => <button key={item.id} type="button" role="tab" aria-selected={item.id === job.id} className="company-job-item" onClick={() => selectJob(item.id)}><span className="font-semibold text-sm">{item.title}</span><span className="text-xs text-muted-foreground flex items-center gap-1">{item.city && <><MapPin className="size-3" />{item.city}</>}{item.mode && item.mode !== item.city ? ` · ${item.mode}` : ''}</span><span className="company-job-count">{item.applicants.toLocaleString('ar-SA')} متقدم</span></button>)}</div>
      </aside>

      <div className="min-w-0 space-y-5">
        <section className="workspace-section company-job-head" aria-labelledby="company-job-title">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 id="company-job-title" className="text-xl font-semibold">{job.title}</h2><p className="text-sm text-muted-foreground mt-1">{[job.city, job.mode, job.salary].filter(Boolean).join(' · ')}</p></div><SpeakButton label={job.title} text={`${job.title}. ${job.description ?? ''} المهارات المطلوبة: ${job.skills.join('، ')}. عدد المتقدمين ${job.applicants}.`} /></div>
          {job.description && <p className="text-sm mt-3">{job.description}</p>}
          <div className="grid gap-5 sm:grid-cols-[minmax(0,1fr)_15rem] mt-5 pt-5 border-t border-border">
            <fieldset><legend className="text-sm font-medium mb-3 flex items-center gap-2"><Filter className="size-4 text-primary" />مهارات يجب أن تتوفر في المرشح</legend><div className="flex flex-wrap gap-2">{job.skills.map(skill => { const on = mustHave.includes(skill); return <Button key={skill} type="button" size="sm" variant={on ? 'secondary' : 'outline'} aria-pressed={on} onClick={() => setMustHave(current => on ? current.filter(item => item !== skill) : [...current, skill])}>{on && <Check />}{skill}</Button>; })}</div><p className="text-xs text-muted-foreground mt-2">نسبة التوافق تُحسب من كل المهارات المطلوبة، والمهارات المختارة هنا شرط لظهور المرشح.</p></fieldset>
            <div><label className="block text-sm font-medium mb-3" id="filter-years-label">سنوات الخبرة</label><Select value={String(job.min_years)} onValueChange={value => void run('years', () => companyApi.setMinYears(job.id, Number(value)))} dir="rtl"><SelectTrigger aria-labelledby="filter-years-label"><SelectValue /></SelectTrigger><SelectContent>{yearOptions.map(option => <SelectItem key={option.value} value={String(option.value)}>{option.label}</SelectItem>)}</SelectContent></Select></div>
          </div>
        </section>

        <section className="workspace-section" aria-labelledby="company-candidates">
          <div className="section-title"><h2 id="company-candidates"><Users />المرشحون المطابقون</h2><span className="text-sm text-muted-foreground">{candidates ? `${candidates.length.toLocaleString('ar-SA')} مرشح` : ''}</span></div>
          {message && <p role="status" className="company-message">{message}</p>}
          {candidates?.[0]?.suggested && <p className="text-sm text-muted-foreground mb-4">لا يوجد متقدمون بعد؛ هؤلاء مرشحون من سند تتوافق مهاراتهم مع الوظيفة.</p>}
          {candidates === null ? <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status"><LoaderCircle className="animate-spin size-4" />جارٍ تحميل المرشحين…</p>
            : candidates.length === 0 ? <p className="text-sm text-muted-foreground">لا يوجد مرشحون بهذه الفلترة. خفّف شروط المهارات أو سنوات الخبرة.</p>
            : <div className="space-y-3">{candidates.map(item => {
              const { talent, status, match } = item;
              const self = talent.id === SELF_TALENT_ID;
              const actions = companyActions(status).filter(action => !(self && action === 'complete'));
              const required = new Set(job.skills.map(skill => skill.toLowerCase()));
              const owned = new Set(talent.skills.map(skill => skill.toLowerCase()));
              return <article key={talent.id} className="company-candidate" aria-label={`المرشح ${talent.name}`}>
                <div className="company-candidate-main">
                  <span className="company-avatar" aria-hidden="true">{talent.name.slice(0, 1)}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold">{talent.name}</h3>{self && <span className="text-xs text-muted-foreground">المرشح الحالي في التجربة</span>}<span className="status-label" data-status={status}>{statusLabels[status]}</span></div>
                    <p className="text-sm text-muted-foreground mt-1 flex flex-wrap items-center gap-x-3 gap-y-1"><span className="company-mode" data-mode={talent.mode}>{talent.mode === 'sign' ? <Hand className="size-4" /> : <AudioLines className="size-4" />}{talent.mode === 'sign' ? 'أصم · مقابلة بمترجم إشارة' : 'كفيف · مقابلة صوتية'}</span><span>{yearsLabel(talent.years)}</span>{talent.city && <span className="flex items-center gap-1"><MapPin className="size-3.5" />{talent.city}</span>}</p>
                  </div>
                  <div className="flex items-center gap-2"><SpeakButton label={`المرشح ${talent.name}`} text={`${talent.name}، توافق ${match} بالمئة، ${yearsLabel(talent.years)}. الحالة: ${statusLabels[status]}.`} /><div className="company-match" style={{ '--match': `${match}%` } as React.CSSProperties} role="img" aria-label={`نسبة التوافق ${match}٪`}><span>{pct(match)}</span></div></div>
                </div>
                <div className="flex flex-wrap gap-2 mt-4">{talent.skills.map(skill => <span key={skill} className="skill-tag" dir="auto" data-match={required.has(skill.toLowerCase())}>{required.has(skill.toLowerCase()) && <Check className="size-3" />}{skill}</span>)}{job.skills.filter(skill => !owned.has(skill.toLowerCase())).map(skill => <span key={skill} className="skill-tag company-missing" dir="auto" title="مهارة مطلوبة غير متوفرة">{skill}</span>)}</div>
                {item.interview_at && ['scheduled', 'nominated'].includes(status) && <p className="text-sm mt-3 flex items-center gap-2"><CalendarDays className="size-4 text-primary" />موعد المقابلة: {formatInterviewDate(item.interview_at)}</p>}
                {self && status === 'scheduled' && <p className="text-xs text-muted-foreground mt-2">بانتظار دخول المرشح إلى المقابلة في موعدها.</p>}
                {status === 'accepted' && <p className="text-xs text-muted-foreground mt-2">بانتظار قبول المرشح للعرض الوظيفي.</p>}
                {scheduling === talent.id ? <div className="flex flex-wrap items-end gap-3 mt-4"><div><label htmlFor={`date-${talent.id}`} className="block text-sm font-medium mb-2">موعد المقابلة · بتوقيت الرياض</label><Input id={`date-${talent.id}`} type="datetime-local" dir="ltr" value={date} onChange={event => setDate(event.target.value)} /></div><Button disabled={busy !== null} onClick={() => confirmSchedule(item)}>{busy === `${talent.id}:schedule` ? <LoaderCircle className="animate-spin" /> : <Check />}تأكيد الموعد</Button><Button variant="ghost" onClick={() => setScheduling(null)}>إلغاء</Button></div>
                  : actions.length > 0 && <div className="flex flex-wrap gap-2 mt-4">{actions.map(action => <Button key={action} disabled={busy !== null} variant={action === 'reject' ? 'outline' : 'default'} onClick={() => act(item, action)}>{busy === `${talent.id}:${action}` && <LoaderCircle className="animate-spin" />}{actionLabels[action]}</Button>)}</div>}
              </article>;
            })}</div>}
        </section>
        <p className="text-xs text-muted-foreground flex flex-wrap items-center gap-2">البيانات محفوظة في قاعدة بيانات سند. <Button variant="link" className="px-0 h-auto text-xs" onClick={() => setConfirmReset(true)}>إعادة البيانات التجريبية</Button></p>
      </div>
    </div>}

    <Dialog open={adding} onOpenChange={setAdding}><DialogContent dir="rtl"><DialogTitle>وظيفة جديدة</DialogTitle><DialogDescription>حدد المسمى والمهارات وسنوات الخبرة. بعد النشر يقترح سند المرشحين المناسبين.</DialogDescription>
      <form onSubmit={event => void addJob(event)} noValidate className="space-y-4">
        <div><label htmlFor="job-title" className="block text-sm font-medium mb-2">المسمى الوظيفي</label><Input id="job-title" maxLength={120} value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} placeholder="مثال: مدخل بيانات" /></div>
        <div><label htmlFor="job-skills" className="block text-sm font-medium mb-2">المهارات المطلوبة (افصل بفاصلة)</label><Input id="job-skills" value={form.skills} onChange={event => setForm({ ...form, skills: event.target.value })} placeholder="Excel، الدقة" /></div>
        <div><label className="block text-sm font-medium mb-2" id="job-years-label">سنوات الخبرة المطلوبة</label><Select value={String(form.years)} onValueChange={value => setForm({ ...form, years: Number(value) })} dir="rtl"><SelectTrigger aria-labelledby="job-years-label"><SelectValue /></SelectTrigger><SelectContent>{yearOptions.map(option => <SelectItem key={option.value} value={String(option.value)}>{option.label}</SelectItem>)}</SelectContent></Select></div>
        {formError && <p role="alert" className="text-sm text-destructive">{formError}</p>}
        <div className="flex gap-2"><Button type="submit"><Send />نشر الوظيفة</Button><Button type="button" variant="ghost" onClick={() => setAdding(false)}><X />إلغاء</Button></div>
      </form>
    </DialogContent></Dialog>
    <Dialog open={confirmReset} onOpenChange={setConfirmReset}><DialogContent dir="rtl"><DialogTitle>إعادة البيانات التجريبية؟</DialogTitle><DialogDescription>تُحذف الوظائف والقرارات التي أضفتها، وترجع الوظائف والمرشحون إلى حالتهم الأولى.</DialogDescription><div className="flex gap-2"><Button onClick={() => { setConfirmReset(false); void run('reset', () => companyApi.reset(), 'رجعت البيانات التجريبية إلى حالتها الأولى.'); }}>نعم، أعد البيانات</Button><Button variant="outline" onClick={() => setConfirmReset(false)}>إلغاء</Button></div></DialogContent></Dialog>
  </Workspace>;
}
