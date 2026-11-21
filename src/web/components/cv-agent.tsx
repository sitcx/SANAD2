/** The candidate's CV, read by the job agent (src/agent/job_agent), and the jobs it matched. */
import { Link } from '@tanstack/react-router';
import { ArrowLeft, BriefcaseBusiness, Check, ExternalLink, FileText, LoaderCircle, MapPin, Upload } from 'lucide-react';
import { useRef } from 'react';
import { Button } from '@/components/ui/button';
import { SpeakButton } from '@/components/speak-button';
import { useSanad } from '@/lib/sanad-context';
import { validateCvFile } from '@/lib/sanad-data';
import { agentCities } from '@/lib/cv-api';
import type { useCvAgent } from '@/hooks/use-cv-agent';

const SHOWN_MATCHES = 5;

type Agent = ReturnType<typeof useCvAgent>;

export function CvAgentCard({ agent }: { agent: Agent }) {
  const state = useSanad();
  const fileInput = useRef<HTMLInputElement>(null);
  const guest = !state.signedIn;
  const profile = guest ? null : agent.data?.profile ?? null;
  const analysing = state.cvStatus === 'analysing';
  const ats = profile?.ats;
  const tips = ats?.checks.filter(check => check.score < 1).sort((a, b) => b.weight - a.weight).slice(0, 2) ?? [];

  function pick() {
    if (guest) { agent.setError('سجّل الدخول أولًا لرفع سيرتك الذاتية.'); return; }
    fileInput.current?.click();
  }

  return <section className="workspace-section dashboard-cv-card" aria-labelledby="cv-title">
    <div className="section-title"><h2 id="cv-title"><FileText />سيرتك الذاتية</h2></div>
    <div className="dashboard-cv-content">
      <div>
        <p className="font-medium text-sm break-all" dir="auto">{(!guest && state.cvName) || 'لم تُضف سيرة ذاتية بعد'}</p>
        {!guest && state.cvName && <p role="status" className="flex items-center gap-2 text-sm text-primary mt-2">
          {analysing ? <><LoaderCircle className="size-5 animate-spin" />يقرأ سند سيرتك ويطابقها مع الوظائف…</>
            : profile ? <><Check className="size-5" />تمت القراءة · جاهزة للتوصيات</> : 'بانتظار القراءة'}
        </p>}
        <p className="text-xs text-muted-foreground mt-3">يقرأ سند سيرتك كما تقرؤها أنظمة التوظيف (ATS)، ثم يحسب توافقها مع كل وظيفة ويبحث لك عن فرص جديدة.</p>
        <input className="sr-only" type="file" ref={fileInput} accept=".pdf,.doc,.docx" aria-label="رفع السيرة الذاتية" onChange={event => {
          const file = event.target.files?.[0];
          event.target.value = '';
          if (!file) return;
          const error = validateCvFile(file.name, file.size);
          if (error) { agent.setError(error); return; }
          void agent.upload(file);
        }} />
        <div className="flex flex-wrap gap-2 mt-4">
          <Button variant="outline" disabled={analysing} onClick={pick}><Upload />{!guest && state.cvName ? 'استبدال السيرة الذاتية' : 'رفع السيرة الذاتية'}</Button>
        </div>
        {agent.needsCity && <div className="mt-4" role="group" aria-labelledby="cv-city">
          <p id="cv-city" className="text-sm font-medium">لم نجد مدينتك في السيرة. أين تفضّل العمل؟</p>
          <div className="flex flex-wrap gap-2 mt-2">{agentCities.map(city => <Button key={city} size="sm" variant="outline" disabled={analysing} onClick={() => agent.answerCity(city)}>{city === 'عن بعد' ? city : <><MapPin />{city}</>}</Button>)}</div>
        </div>}
        {agent.error && <p role="alert" className="text-xs text-destructive mt-3">{agent.error}{guest && <> <Link to="/login" className="underline font-semibold">تسجيل الدخول</Link></>}</p>}
      </div>
      <div>
        {profile ? <>
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-semibold text-sm">المهارات المستخرجة</h3>
            <SpeakButton label="ملخص سيرتك" text={`${profile.summary} المهارات: ${profile.skills.join('، ')}.${ats ? ` تقييم السيرة في أنظمة التوظيف ${ats.score} من 100.` : ''}`} />
          </div>
          <div className="flex flex-wrap gap-2 mt-3">{profile.skills.map(skill => <span className="skill-tag" key={skill} dir="auto">{skill}</span>)}</div>
          {profile.experience.length > 0 && <><h3 className="font-semibold text-sm mt-5">الخبرات</h3><ul className="space-y-1 mt-2 text-sm text-muted-foreground">{profile.experience.map(item => <li key={item} dir="auto">{item}</li>)}</ul></>}
          {ats && <><h3 className="font-semibold text-sm mt-5">تقييم السيرة في أنظمة التوظيف: {ats.score.toLocaleString('ar-SA')}/١٠٠ · {ats.rating}</h3>
            {tips.length > 0 && <ul className="space-y-1 mt-2 text-xs text-muted-foreground">{tips.map(tip => <li key={tip.id}>{tip.tip}</li>)}</ul>}</>}
        </> : <p className="text-sm text-muted-foreground">ستظهر المهارات والخبرات والوظائف المناسبة بعد قراءة سيرتك.</p>}
      </div>
    </div>
  </section>;
}

export function AgentMatches({ agent }: { agent: Agent }) {
  const state = useSanad();
  const matches = agent.data?.matches.slice(0, SHOWN_MATCHES) ?? [];
  if (!state.signedIn || !agent.data?.profile) return null;
  return <section className="workspace-section" aria-labelledby="matching-title">
    <div className="section-title"><h2 id="matching-title"><BriefcaseBusiness />الوظائف المناسبة لك</h2><Button asChild variant="link" className="px-0"><Link to="/jobs">كل الوظائف<ArrowLeft /></Link></Button></div>
    {matches.length === 0 ? <p className="text-sm text-muted-foreground">لم نجد وظائف مطابقة بعد. يبحث سند عن فرص جديدة في الخلفية؛ عُد بعد قليل.</p>
      : <ul className="space-y-4">{matches.map(({ job, match, reason, missing_skills: missing }) => <li key={job.id} className="rounded-lg border p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="font-semibold" dir="auto">{job.title}</h3>
            <p className="text-sm text-muted-foreground mt-1" dir="auto">{[job.company, job.city, job.mode].filter(Boolean).join(' · ')}</p>
          </div>
          <span className="text-sm font-semibold text-primary shrink-0">{match.toLocaleString('ar-SA')}٪ توافق</span>
        </div>
        <p className="text-sm mt-3 leading-loose">{reason}</p>
        {missing.length > 0 && <div className="flex flex-wrap gap-2 mt-3" aria-label="مهارات ينصح بتطويرها">{missing.slice(0, 4).map(skill => <span className="skill-tag" key={skill} dir="auto">{skill}</span>)}</div>}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <SpeakButton label={`وظيفة ${job.title}`} text={`${job.title}${job.company ? ` لدى ${job.company}` : ''}. توافق ${match} بالمئة. ${reason}`} />
          {job.source_url && <Button asChild variant="link" className="px-0"><a href={job.source_url} target="_blank" rel="noopener noreferrer">عرض الإعلان{job.source_name ? ` في ${job.source_name}` : ''}<ExternalLink /></a></Button>}
        </div>
      </li>)}</ul>}
  </section>;
}
