import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, ArrowRight, BriefcaseBusiness, Check, FileText, LoaderCircle, Upload } from 'lucide-react';
import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { DailySkillCard } from '@/components/daily-skill-card';
import { InterviewCalendar } from '@/components/interview-calendar';
import { JobCard } from '@/components/job-card';
import { useSanad } from '@/lib/sanad-context';
import { jobs, mockCvProfile, validateCvFile } from '@/lib/sanad-data';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/dashboard')({ head: () => pageHead('لوحة التحكم', 'مهارة مهنية مفيدة مع مثال عملي، تقويم مواعيدك، سيرتك الذاتية والوظائف المناسبة لك في مساحة واحدة.'), component: Dashboard });
function Dashboard() {
  const state = useSanad();
  const fileInput = useRef<HTMLInputElement>(null);
  const [fileError, setFileError] = useState('');
  const guest = !state.signedIn;
  return <Workspace><Button asChild variant="ghost" className="mb-2 px-2"><Link to="/" aria-label="العودة إلى الرئيسية"><ArrowRight />العودة إلى الرئيسية</Link></Button><PageTitle title="لوحة التحكم" subtitle={`مرحبًا ${state.candidateName}، لنجهّز خطوتك القادمة.`} />
    <div className="dashboard-overview">
      <DailySkillCard />
    <section className="workspace-section dashboard-cv-card" aria-labelledby="cv-title"><div className="section-title"><h2 id="cv-title"><FileText />سيرتك الذاتية</h2></div><div className="dashboard-cv-content"><div><p className="font-medium text-sm break-all" dir="auto">{(!guest && state.cvName) || 'لم تُضف سيرة ذاتية بعد'}</p>{!guest && <p role="status" className="flex items-center gap-2 text-sm text-primary mt-2">{state.cvStatus === 'analysed' ? <><Check className="size-5" />تم التحليل · جاهزة للتوصيات</> : state.cvStatus === 'analysing' ? <><LoaderCircle className="size-5 animate-spin" />جارٍ تحليل السيرة الذاتية…</> : 'تم رفع الملف · بانتظار التحليل'}</p>}<p className="text-xs text-muted-foreground mt-3">تحليل تجريبي بمهارات افتراضية، دون قراءة محتوى الملف أو رفعه.</p><input className="sr-only" type="file" ref={fileInput} accept=".pdf,.doc,.docx" aria-label="رفع السيرة الذاتية" onChange={event => { if (guest) { setFileError('سجّل الدخول أولًا لرفع سيرتك الذاتية.'); event.target.value = ''; return; } const file = event.target.files?.[0]; if (!file) return; const error = validateCvFile(file.name, file.size); if (error) { setFileError(error); event.target.value = ''; return; } state.setCvName(file.name); state.setCvStatus('uploaded'); setFileError(''); event.target.value = ''; }} /><div className="flex flex-wrap gap-2 mt-4"><Button variant="outline" disabled={state.cvStatus === 'analysing'} onClick={() => { if (guest) { setFileError('سجّل الدخول أولًا لرفع سيرتك الذاتية.'); return; } fileInput.current?.click(); }}><Upload />{state.cvName ? 'استبدال السيرة الذاتية' : 'رفع السيرة الذاتية'}</Button>{!guest && state.cvStatus !== 'analysed' && <Button disabled={state.cvStatus === 'analysing' || !state.cvName} onClick={() => state.setCvStatus('analysing')}><FileText />تحليل السيرة الذاتية</Button>}</div>{fileError && <p role="alert" className="text-xs text-destructive mt-3">{fileError}{guest && <> <Link to="/login" className="underline font-semibold">تسجيل الدخول</Link></>}</p>}</div><div>{!guest && state.cvStatus === 'analysed' ? <><h3 className="font-semibold text-sm">المهارات المستخرجة · نموذج تجريبي</h3><div className="flex flex-wrap gap-2 mt-3">{mockCvProfile.skills.map(skill => <span className="skill-tag" key={skill}>{skill}</span>)}</div><h3 className="font-semibold text-sm mt-5">الخبرات</h3><ul className="space-y-1 mt-2 text-sm text-muted-foreground">{mockCvProfile.experience.map(item => <li key={item}>{item}</li>)}</ul></> : <p className="text-sm text-muted-foreground">ستظهر المهارات والخبرات والوظائف المناسبة بعد اكتمال التحليل التجريبي.</p>}</div></div></section>
      <InterviewCalendar empty={guest} />
    </div>
    {!guest && state.cvName && <><section className="workspace-section" aria-labelledby="matching-title"><div className="section-title"><h2 id="matching-title"><BriefcaseBusiness />الوظائف المناسبة لك</h2><Button asChild variant="link" className="px-0"><Link to="/jobs">كل الوظائف<ArrowLeft /></Link></Button></div>{state.cvStatus === 'analysed' ? <div className="space-y-4">{jobs.map(job => <JobCard key={job.id} job={job} />)}</div> : <p className="text-sm text-muted-foreground">أكمل تحليل سيرتك لتظهر توصيات الوظائف ومدى التوافق.</p>}</section></>}
  </Workspace>;
}
