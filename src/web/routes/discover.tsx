import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { ArrowLeft, ArrowRight, Compass, RotateCcw, Volume2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { JobCard } from '@/components/job-card';
import { SpeakButton } from '@/components/speak-button';
import { PageTitle, ProgressBar, Workspace } from '@/components/sanad-layout';
import { careerQuestions, rankCareerTracks, type CareerTrackId } from '@/lib/career-discovery';
import { useSanad } from '@/lib/sanad-context';
import { jobs } from '@/lib/sanad-data';
import { speak } from '@/lib/voice-guide';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/discover')({ head: () => pageHead('اكتشف مسارك المهني', 'أسئلة عامة عن ميولك تقترح عليك المسار المهني والوظائف المناسبة. الخطوة اختيارية.'), component: Discover });

function Discover() {
  const state = useSanad();
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<CareerTrackId[]>([]);
  const voice = state.communicationMode === 'voice';
  const index = answers.length;
  const question = careerQuestions[index];
  const progress = Math.round(index / careerQuestions.length * 100);
  const questionText = question ? `${question.question} ${question.options.map((option, i) => `الخيار ${i + 1}: ${option.label}`).join('. ')}` : '';
  useEffect(() => { if (voice && questionText) speak(questionText); }, [voice, questionText]);

  function skip() { state.skipCareerDiscovery(); void navigate({ to: '/dashboard' }); }

  if (!question) {
    const ranked = rankCareerTracks(answers);
    const top = ranked[0]!;
    const suggested = jobs.filter(job => top.track.jobIds.includes(job.id));
    return <Workspace><PageTitle title="مسارك المهني المقترح" subtitle={`أقرب مسار لميولك: ${top.track.label}`} />
      <section className="workspace-section" aria-labelledby="career-result">
        <div className="section-title"><h2 id="career-result"><Compass />{top.track.label}</h2><div className="flex items-center gap-2"><SpeakButton label="نتيجة المسار" text={`مسارك المقترح: ${top.track.label}. ${top.track.description} ${ranked.map(item => `${item.track.label} ${item.percent} بالمئة`).join('، ')}.`} /><span className="text-sm text-primary font-semibold">{top.percent.toLocaleString('ar-SA')}٪</span></div></div>
        <p className="text-sm text-muted-foreground">{top.track.description}</p>
        <ul className="grid gap-3 mt-5">{ranked.map(item => <li key={item.track.id}><div className="flex justify-between text-sm mb-1"><span>{item.track.label}</span><span>{item.percent.toLocaleString('ar-SA')}٪</span></div><ProgressBar value={item.percent} label={item.track.label} /></li>)}</ul>
        <div className="flex flex-wrap gap-3 mt-6"><Button onClick={() => { state.completeCareerDiscovery(top.track.id); void navigate({ to: '/dashboard' }); }}>اعتماد المسار والمتابعة<ArrowLeft /></Button><Button variant="outline" onClick={() => setAnswers([])}><RotateCcw />إعادة الأسئلة</Button></div>
      </section>
      {suggested.length > 0 && <section className="workspace-section" aria-labelledby="career-jobs"><div className="section-title"><h2 id="career-jobs">وظائف في هذا المسار</h2></div><div className="space-y-4">{suggested.map(job => <JobCard key={job.id} job={job} />)}</div></section>}
    </Workspace>;
  }

  return <Workspace><Button asChild variant="ghost" className="mb-2 px-2"><Link to="/dashboard"><ArrowRight />العودة إلى لوحة التحكم</Link></Button>
    <PageTitle title="اكتشف مسارك المهني" subtitle="أجب عن أسئلة عامة عن ميولك، وسنقترح عليك المسار الأنسب. إذا كنت تعرف مسارك يمكنك تخطي هذه الخطوة." action={<Button variant="ghost" onClick={skip}>أعرف مساري، تخطَّ</Button>} />
    <section className="workspace-section" aria-labelledby="career-question">
      <div className="flex justify-between text-sm text-muted-foreground mb-2"><span>السؤال {(index + 1).toLocaleString('ar-SA')} من {careerQuestions.length.toLocaleString('ar-SA')}</span><span>{progress.toLocaleString('ar-SA')}٪</span></div>
      <ProgressBar value={progress} label="التقدم في أسئلة المسار المهني" />
      <h2 id="career-question" className="text-xl font-semibold mt-6" aria-live="polite">{question.question}</h2>
      <div className="grid sm:grid-cols-2 gap-3 mt-5">{question.options.map((option, i) => <Button key={option.track} variant="outline" className="h-auto min-h-14 justify-start whitespace-normal text-start py-3" onClick={() => setAnswers(current => [...current, option.track])}><span className="text-primary font-semibold">{(i + 1).toLocaleString('ar-SA')}</span>{option.label}</Button>)}</div>
      <div className="flex flex-wrap gap-3 mt-5">{index > 0 && <Button variant="ghost" onClick={() => setAnswers(current => current.slice(0, -1))}><ArrowRight />السؤال السابق</Button>}{voice && <Button variant="outline" onClick={() => speak(questionText)}><Volume2 />استمع للسؤال</Button>}</div>
    </section>
  </Workspace>;
}
