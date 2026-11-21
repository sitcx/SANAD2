import { useEffect, useState } from 'react';
import { Link } from '@tanstack/react-router';
import { ArrowLeft, AudioLines, Mic, MicOff, PhoneOff, UserRound, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { useSanad } from '@/lib/sanad-context';
import { liveQuestionSets, type Job } from '@/lib/sanad-data';
import { speak, stopSpeaking } from '@/lib/voice-guide';

export const voiceJoinGuide = 'أهلًا بك في المقابلة الصوتية. ستسمع مسؤول التوظيف وتجيبه مباشرة بصوتك، دون الحاجة إلى رؤية الشاشة. اضغط زر الانضمام للدخول، وزر إنهاء المقابلة في الأسفل للخروج.';

/** Preparation for blind candidates: no camera, spoken instructions, one join button. */
export function VoiceInterviewPreparation({ job, preview, onJoin }: { job: Job; preview: boolean; onJoin: () => void }) {
  useEffect(() => { speak(voiceJoinGuide); return stopSpeaking; }, []);
  return <section className="workspace-section" aria-labelledby="voice-prep-title">
    <h2 id="voice-prep-title" className="text-xl font-semibold flex items-center gap-2"><AudioLines className="text-primary" />مقابلة صوتية</h2>
    <p className="text-sm text-muted-foreground mt-3">{job.title} · {job.company}</p>
    <p className="mt-4 leading-loose">{voiceJoinGuide}</p>
    <div className="flex flex-wrap gap-3 mt-6"><Button size="lg" onClick={onJoin}>{preview ? 'ابدأ تجربة المقابلة' : 'انضم إلى المقابلة'}<ArrowLeft /></Button><Button size="lg" variant="outline" onClick={() => speak(voiceJoinGuide)}><Volume2 />أعد الاستماع للتعليمات</Button></div>
  </section>;
}

/**
 * Voice interview: the candidate hears the interviewer and answers directly by voice.
 * The company hears the answers itself, so nothing is converted to text.
 */
export function VoiceMeetingRoom({ job, preview = false, candidateName }: { job: Job; preview?: boolean; candidateName: string }) {
  const state = useSanad();
  const questions = liveQuestionSets[job.id];
  const [index, setIndex] = useState(0);
  const [mic, setMic] = useState(true);
  const [seconds, setSeconds] = useState(0);
  const [ending, setEnding] = useState(false);
  const [notice, setNotice] = useState('بدأت المقابلة الصوتية.');
  const question = questions[index]?.original ?? '';
  useEffect(() => { const timer = window.setInterval(() => setSeconds(current => current + 1), 1000); return () => window.clearInterval(timer); }, []);
  // Simulates the interviewer's voice: each question is spoken aloud.
  useEffect(() => { if (question) speak(`مسؤول التوظيف يسأل: ${question}`); }, [question]);
  useEffect(() => stopSpeaking, []);
  function announce(message: string) { setNotice(message); speak(message); }
  return <section className="meeting-shell" aria-labelledby="voice-meeting-title">
    <header className="meeting-header"><div><h1 className="meeting-heading" id="voice-meeting-title">{preview ? 'تجربة المقابلة الصوتية' : 'المقابلة الصوتية'}</h1><p className="text-xs text-meeting-muted mt-1">{job.title} · {job.company} · محاكاة</p></div><span className="text-xs text-meeting-muted tabular-nums" aria-label="مدة المقابلة">{Math.floor(seconds / 60).toLocaleString('ar-SA')}:{String(seconds % 60).padStart(2, '0')}</span></header>
    <div className="meeting-notice" role="status" aria-live="assertive"><Volume2 className="size-5 text-meeting-accent shrink-0" /><span>{notice}</span></div>
    <div className="grid sm:grid-cols-2 gap-4 mt-4">
      <div className="meeting-video" aria-label="مسؤول التوظيف"><div className="meeting-inset-placeholder"><UserRound className="size-12" /><p>خالد · مسؤول التوظيف</p><span>اتصال صوتي</span></div></div>
      <div className="meeting-video" aria-label={`${candidateName} · المرشح`}><div className="meeting-inset-placeholder">{mic ? <Mic className="size-12" /> : <MicOff className="size-12" />}<p>{candidateName} · المرشح</p><span>{mic ? 'الميكروفون يعمل · أجب بصوتك مباشرة' : 'الميكروفون مكتوم'}</span></div></div>
    </div>
    <p className="text-sm text-meeting-muted mt-4">السؤال {(index + 1).toLocaleString('ar-SA')} من {questions.length.toLocaleString('ar-SA')} · يسمع مسؤول التوظيف إجابتك مباشرة، ولا تتحول إلى نص.</p>
    <footer className="meeting-toolbar"><div className="meeting-tools">
      <Button className="meeting-outline" aria-pressed={!mic} onClick={() => { setMic(!mic); announce(mic ? 'تم كتم الميكروفون.' : 'تم تشغيل الميكروفون.'); }}>{mic ? <MicOff /> : <Mic />}{mic ? 'كتم الميكروفون' : 'تشغيل الميكروفون'}</Button>
      <Button className="meeting-outline" onClick={() => speak(`مسؤول التوظيف يسأل: ${question}`)}><Volume2 />أعد السؤال</Button>
      <Button className="meeting-primary" disabled={index >= questions.length - 1} onClick={() => setIndex(current => current + 1)}>محاكاة السؤال التالي<ArrowLeft /></Button>
    </div><Button variant="destructive" onClick={() => { setEnding(true); speak('هل تريد إنهاء المقابلة؟'); }}><PhoneOff />إنهاء المقابلة</Button></footer>
    <Dialog open={ending} onOpenChange={setEnding}><DialogContent dir="rtl"><DialogTitle>هل تريد إنهاء المقابلة؟</DialogTitle><DialogDescription>{preview ? 'لن تغيّر التجربة حالة طلبك.' : 'تنتهي المقابلة وتتحدث حالة طلبك إلى «المقابلة مكتملة».'}</DialogDescription><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => setEnding(false)}>متابعة المقابلة</Button><Button asChild>{preview ? <Link to="/dashboard">إنهاء التجربة والعودة<ArrowLeft /></Link> : <Link to="/applications" onClick={() => state.finishInterview(questions.slice(0, index + 1).map(item => item.original), seconds)}>إنهاء المقابلة<ArrowLeft /></Link>}</Button></div></DialogContent></Dialog>
  </section>;
}
