import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, ArrowRight, Check, CircleCheck, Hand, Lightbulb, MessageSquareText, RotateCcw, Send, Target } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { PageTitle, ProgressBar, Workspace } from '@/components/sanad-layout';
import { coachQuestions, jobs } from '@/lib/sanad-data';
import { useSanad } from '@/lib/sanad-context';
import { pageHead } from '@/lib/page-head';
import { getTrainingReadiness } from '@/lib/training-readiness';

export const Route = createFileRoute('/coach')({ head: () => pageHead('مدرب المقابلة', 'تدرّب على أسئلة المقابلة بالعربية المبسطة واحصل على ملاحظات داعمة.'), component: Coach });
function Coach() {
  const state = useSanad();
  return <CoachSession key={state.selectedJobId} />;
}
function CoachSession() {
  const state = useSanad();
  const [index, setIndex] = useState(0);
  const [phase, setPhase] = useState<'question' | 'answer' | 'feedback' | 'complete'>('question');
  const [answer, setAnswer] = useState('');
  const [signOpen, setSignOpen] = useState(false);
  const question = index === 2 && state.selectedJobId !== 'analyst' ? { original: 'كيف تعاملت مع تحدٍ واجهك في عملك؟', simple: 'احكِ عن مشكلة في عملك. كيف حللتها؟' } : coachQuestions[index] ?? coachQuestions[0];
  const job = jobs.find(item => item.id === state.selectedJobId) ?? jobs[0];
  const trainingReadiness = getTrainingReadiness(state.trainingProgress[job.id]);
  function nextQuestion() { if (index === coachQuestions.length - 1) { setPhase('complete'); } else { setIndex(index + 1); setAnswer(''); setPhase('question'); } }
  return <Workspace><Button asChild variant="ghost" className="mb-2 px-2"><Link to="/dashboard" aria-label="العودة إلى لوحة التحكم"><ArrowRight />العودة إلى لوحة التحكم</Link></Button><PageTitle title="التدريب على المقابلة" subtitle={`تدريبك على مقابلة ${job.title} · ${job.company}`} />
    <div className="flex flex-wrap justify-between items-center gap-2 text-sm mb-3"><span className="text-muted-foreground">تدريب المقابلة</span><Button variant="ghost" size="icon" aria-label="السؤال السابق" disabled={index === 0 || phase === 'complete'} onClick={() => { setIndex(index - 1); setAnswer(''); setPhase('question'); }}><ArrowRight /></Button><span className="text-primary font-medium">{phase === 'complete' ? '٨ من ٨ أسئلة' : `السؤال ${(index + 1).toLocaleString('ar-SA')} من ٨`}</span></div><ProgressBar value={trainingReadiness} label="جاهزية التدريب" /><p role="status" className="text-sm text-muted-foreground mt-3">{trainingReadiness.toLocaleString('ar-SA')}٪ جاهزية التدريب · نسبة الأسئلة المكتملة، وليست تقييمًا لجودة الإجابات.</p>
    {phase === 'complete' ? <section className="surface mt-6 text-center py-12" aria-live="polite"><CircleCheck className="size-14 text-primary mx-auto" /><h2 className="text-2xl font-semibold mt-5">أحسنت يا {state.candidateName}!</h2><p className="text-muted-foreground mt-3 text-sm">أكملت ٨ أسئلة. جاهزية تدريبك لهذه الوظيفة {trainingReadiness.toLocaleString('ar-SA')}٪.</p><div className="flex flex-wrap justify-center gap-3 mt-7"><Button asChild><Link to="/dashboard">العودة إلى لوحة التحكم<ArrowLeft /></Link></Button><Button variant="outline" onClick={() => { setIndex(0); setAnswer(''); setPhase('question'); }}><RotateCcw />تدرّب مرة أخرى</Button></div></section> : <div className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] mt-6">
      <section className="surface"><span className="status-label"><Target className="size-4" />سؤال المقابلة</span><h2 className="text-xl font-semibold leading-loose mt-5">{question.original}</h2><div className="border-t border-border mt-6 pt-5"><p className="text-xs text-primary font-medium flex gap-2 items-center"><MessageIcon />بكلمات أبسط</p><p className="text-lg mt-3 leading-loose">{question.simple}</p></div><Button variant="ghost" className="mt-5 px-0 text-primary" aria-expanded={signOpen} onClick={() => setSignOpen(!signOpen)}><Hand />عرض لغة الإشارة</Button>{signOpen && <div role="status" className="answer-bubble mt-3"><Hand className="size-6 mb-2" /><p>مساحة فيديو لغة الإشارة</p><p className="text-xs mt-1">الفيديو غير متاح في النموذج التجريبي. السؤال المبسط متاح نصيًا أعلاه.</p></div>}<div className="flex items-start gap-2 mt-5 text-xs text-muted-foreground"><Lightbulb className="size-4 text-peach-foreground shrink-0 mt-0.5" /><p>فكّر في مثال حقيقي: ما المشكلة، ماذا فعلت، وما النتيجة؟</p></div></section>
      <div><div className="practice-prompt"><Target className="size-7 text-primary" /><h3 className="font-semibold mt-3">إجابتك التدريبية</h3><p className="text-sm text-muted-foreground mt-2">خذ وقتك لتعبّر عن مهاراتك وخبراتك.</p></div>
        {phase === 'question' && <Button className="w-full mt-4" size="lg" onClick={() => setPhase('answer')}><Hand />ابدأ الإجابة</Button>}
        {phase === 'answer' && <form className="mt-4" onSubmit={e => { e.preventDefault(); if (!answer.trim()) return; state.completeTrainingQuestion(job.id, index); setPhase('feedback'); }}><label htmlFor="practice-answer" className="block text-sm font-medium mb-2">إجابتك</label><Textarea id="practice-answer" value={answer} onChange={e => setAnswer(e.target.value)} required placeholder="اكتب إجابتك للتدرّب..." rows={4} /><Button className="w-full mt-3" type="submit" disabled={!answer.trim()}><Send />إنهاء الإجابة</Button></form>}
      </div>
      {phase === 'feedback' && <section className="surface lg:col-span-2" aria-live="polite"><div className="flex items-center gap-2"><CircleCheck className="size-6 text-primary" /><h2 className="text-lg font-semibold">خطوة موفّقة يا {state.candidateName}</h2><span className="status-label mr-auto">ملاحظات تدريبية تجريبية</span></div><p className="text-sm text-muted-foreground mt-3 border-b border-border pb-4">«{answer}»</p><div className="grid gap-5 sm:grid-cols-2 mt-5"><div><h3 className="text-sm font-semibold text-primary">نقاط القوة</h3><ul className="space-y-2 text-sm mt-2"><li className="flex items-start gap-2"><Check className="size-4 text-primary mt-1 shrink-0" />أخذت وقتك لصياغة إجابة خاصة بك.</li><li className="flex items-start gap-2"><Check className="size-4 text-primary mt-1 shrink-0" />عبّرت عن خبرتك بطريقتك، دون ضغط الوقت.</li></ul></div><div><h3 className="text-sm font-semibold text-primary">المهارات التي أظهرتها · مثال تجريبي</h3><div className="flex flex-wrap gap-2 my-3">{['التواصل الكتابي', 'تنظيم الأفكار'].map(skill => <span key={skill} className="skill-tag">{skill}</span>)}</div><h3 className="text-sm font-semibold text-peach-foreground">اقتراح للتطوير</h3><p className="text-sm text-muted-foreground mt-2">أضف نتيجة محددة أو رقمًا يوضح أثر ما فعلته، واجعل ترتيب إجابتك: التحدي، الإجراء، النتيجة.</p></div></div><div className="flex flex-wrap gap-3 justify-end mt-5"><Button variant="outline" onClick={() => setPhase('answer')}><RotateCcw />أحاول مرة أخرى</Button><Button onClick={nextQuestion}>{index === 7 ? 'إنهاء التدريب' : 'السؤال التالي'}<ArrowLeft /></Button></div></section>}
    </div>}
  </Workspace>;
}
function MessageIcon() { return <MessageSquareText className="size-5" />; }