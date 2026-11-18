import { useEffect, useState } from 'react';
import { Link } from '@tanstack/react-router';
import { ArrowLeft, Bell, Check, Clock3, Captions, EarOff, Hand, LoaderCircle, MessageSquareText, MonitorSmartphone, PhoneOff, RotateCcw, Settings2, ShieldCheck, Smile, Video, VideoOff, UserRound, Pencil, Wifi, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Switch } from '@/components/ui/switch';
import type { LocalMedia } from '@/hooks/use-local-media';
import type { InterviewCommunication } from '@/components/interview-preparation';
import { useSanad } from '@/lib/sanad-context';
import { approveAnswer, liveQuestionSets, reactionRecipient, reactions, type Job, type MeetingSide } from '@/lib/sanad-data';

export function MeetingRoom({ job, preview = false, media, candidateName, communication }: { job: Job; preview?: boolean; media: LocalMedia; candidateName: string; communication: InterviewCommunication }) {
  const state = useSanad();
  const questions = liveQuestionSets[job.id];
  const [view, setView] = useState<'both' | MeetingSide>('candidate');
  const [signRequested, setSignRequested] = useState(false);
  const [conversationOpen, setConversationOpen] = useState(true);
  const [captions, setCaptions] = useState(true);
  const [previewAnswers, setPreviewAnswers] = useState<string[]>([]);
  const answers = preview ? previewAnswers : state.sentAnswers;
  const [index, setIndex] = useState(0);
  const [customQuestion, setCustomQuestion] = useState('');
  const [postedQuestion, setPostedQuestion] = useState('');
  const [draft, setDraft] = useState('');
  const [review, setReview] = useState(false);
  const [translating, setTranslating] = useState(false);
  const [approved, setApproved] = useState<string | null>(null);
  const [approvedQuestions, setApprovedQuestions] = useState<string[]>([]);
  const [connected, setConnected] = useState(true);
  const [seconds, setSeconds] = useState(0);
  const [answerSeconds, setAnswerSeconds] = useState(120);
  const [notice, setNotice] = useState('بدأت المقابلة. وصل السؤال الأول إلى المرشح.');
  const [notifications, setNotifications] = useState(true);
  const [haptic, setHaptic] = useState(false);
  const [dialog, setDialog] = useState<'reactions' | 'settings' | 'devices' | 'end' | null>(null);
  const [sender, setSender] = useState<MeetingSide>('recruiter');
  const [reaction, setReaction] = useState<{ item: typeof reactions[number]; recipient: MeetingSide; key: number } | null>(null);
  const [linked, setLinked] = useState(false);
  const question = questions[index] ?? questions[0];
  const original = postedQuestion || question?.original || '';
  const simple = postedQuestion || question?.simple || '';
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'instant' }); }, []);
  useEffect(() => { const timer = window.setInterval(() => { setSeconds(current => current + 1); setAnswerSeconds(current => Math.max(0, current - 1)); }, 1000); return () => window.clearInterval(timer); }, []);
  useEffect(() => { if (!reaction) return; const timer = window.setTimeout(() => setReaction(null), 4500); return () => window.clearTimeout(timer); }, [reaction]);
  useEffect(() => { if (!translating) return; const timer = window.setTimeout(() => { setDraft(question?.answer ?? ''); setReview(true); setTranslating(false); }, 800); return () => window.clearTimeout(timer); }, [translating, question]);
  function announce(message: string) { setNotice(message); if (haptic && typeof navigator.vibrate === 'function') navigator.vibrate(80); }
  function sendApproved() {
    if (!review || !connected || approved !== null) return;
    const answer = approveAnswer(draft, true); if (answer === null) return;
    if (preview) setPreviewAnswers(current => [...current, answer]); else state.setSentAnswers([...state.sentAnswers, answer]); setApprovedQuestions(current => [...current, original]); setApproved(answer); setDraft(''); setReview(false);
    announce('وصلت الإجابة المعتمدة إلى مسؤول التوظيف.');
  }
  function nextQuestion() {
    if (index >= questions.length - 1 || !connected) return;
    setIndex(current => current + 1); setPostedQuestion(''); setDraft(''); setApproved(null); setReview(false); setAnswerSeconds(120); announce('وصل سؤال جديد إلى المرشح.');
  }
  function sendReaction(item: typeof reactions[number]) {
    if (!connected) return;
    const recipient = reactionRecipient(sender);
    setReaction({ item, recipient, key: Date.now() }); setDialog(null);
    announce(`تفاعل من ${sender === 'recruiter' ? 'مسؤول التوظيف' : candidateName}: ${item.label}`);
  }
  function reactionOverlay(side: MeetingSide) {
    return reaction?.recipient === side && <div key={reaction.key} className="reaction-overlay" role="status"><span className="reaction-symbol">{reaction.item.symbol}</span><span>{reaction.item.label}</span><span className="reaction-particles" aria-hidden="true"><span>✦</span><span>✦</span><span>✦</span></span></div>;
  }
  function video(side: MeetingSide) {
    const candidate = side === 'candidate';
    return <div className={candidate ? 'meeting-candidate-inset' : 'meeting-video'} aria-label={candidate ? 'فيديو المرشح' : 'فيديو مسؤول التوظيف'}>
      {candidate && <video ref={media.videoRef} autoPlay playsInline muted className={media.camera ? 'local-camera' : 'local-camera hidden'} aria-label="معاينة الكاميرا المحلية" />}
      {(!candidate || !media.camera) && <div className="meeting-inset-placeholder"><UserRound className="size-9" /><p>{candidate ? candidateName : 'خالد'}</p><span>{candidate ? 'الكاميرا متوقفة' : 'فيديو غير متصل'}</span></div>}
      <div className="meeting-video-caption"><span>{candidate ? `${candidateName} · المرشح` : 'خالد · مسؤول التوظيف'}</span>{!candidate && <WifiOff className="size-4" />}</div>
      {reactionOverlay(side)}
    </div>;
  }
  return <section className="meeting-shell" aria-labelledby="meeting-title"><header className="meeting-header"><div><h1 className="meeting-heading" id="meeting-title">{preview ? 'تجربة المقابلة الوظيفية' : 'غرفة المقابلة'}</h1><p className="text-xs text-meeting-muted mt-1">{job.title} · {job.company} · محاكاة</p></div><div className="flex flex-wrap gap-4 items-center"><span className="meeting-status"><span className="meeting-status-dot" />{preview ? 'تجربة مفتوحة · لا تغيّر طلبك' : 'المقابلة جارية الآن'}</span><span className="text-xs text-meeting-muted tabular-nums" aria-label="مدة المقابلة">{Math.floor(seconds / 60).toLocaleString('ar-SA')}:{String(seconds % 60).padStart(2, '0')}</span></div>{view !== 'candidate' && <div className="meeting-view-controls" role="group" aria-label="عرض الجهازين">{[{ id: 'both', label: 'الشاشتان' }, { id: 'candidate', label: 'جهاز المرشح' }, { id: 'recruiter', label: 'جهاز مسؤول التوظيف' }].map(item => <Button variant="ghost" key={item.id} aria-pressed={view === item.id} onClick={() => setView(item.id as typeof view)}>{item.label}</Button>)}</div>}</header>
    {(notifications || !connected) && <div className="meeting-notice" role={connected ? 'status' : 'alert'}>{connected ? <Bell className="size-5 text-meeting-accent shrink-0" /> : <WifiOff className="size-5 shrink-0" />}<span>{connected ? notice : 'مشكلة في الاتصال التجريبي. الإرسال متوقف حتى استعادة الاتصال.'}</span></div>}
    {media.error && <p role="alert" className="media-error"><VideoOff className="size-5 shrink-0" />{media.error}</p>}
    <div className="meeting-grid" data-view={view} data-conversation={conversationOpen}>
      {view !== 'recruiter' && <section className="meeting-candidate-workspace" aria-label="جهة المرشح">
        <div className="meeting-sign-stage" aria-label="مساحة لغة الإشارة">
          <div className="meeting-stage-panes" data-split={state.interpreterRequested ? 'true' : 'false'}>
            <div className="meeting-stage-pane"><UserRound className="size-14" /><span className="meeting-speaker">خالد · مسؤول التوظيف · محاكاة</span></div>
            {state.interpreterRequested && <div className="meeting-stage-pane meeting-stage-pane-interpreter"><Hand className="size-14" /><span className="meeting-speaker">مترجم لغة الإشارة</span><div className="meeting-stage-notice" role="status"><EarOff className="size-4" />طلب المترجم مسجّل في هذه الجلسة · غير متصل في النموذج</div></div>}
          </div>
          {video('candidate')}
          <div className="meeting-sign-actions"><Button className="meeting-primary meeting-sign-start" onClick={() => setSignRequested(true)}><Hand />{signRequested ? 'لغة الإشارة غير متاحة حاليًا' : 'ابدأ الإشارة'}</Button>{signRequested && <p role="status" className="meeting-sign-note">تحويل الكلام إلى لغة الإشارة غير متصل في النموذج.</p>}</div>
          <div className="meeting-interpreter"><Button className="meeting-outline meeting-interpreter-button" aria-pressed={state.interpreterRequested} disabled={state.interpreterRequested} onClick={() => { state.setInterpreterRequested(true); announce('تم تسجيل حاجتك إلى مترجم. الطلب غير متصل في النموذج.'); }}><EarOff />{state.interpreterRequested ? 'تم تسجيل الحاجة إلى مترجم' : 'الحاجة إلى مترجم'}</Button></div>
          {captions && <div className="meeting-stage-captions"><span>نص السؤال · محاكاة</span><p>{original}</p></div>}
        </div>
        {conversationOpen && <section className="meeting-conversation" aria-label="المحادثة والترجمة">
          <header className="meeting-conversation-header"><h2><MessageSquareText className="size-5" />المحادثة والترجمة</h2><span>السؤال {(index + 1).toLocaleString('ar-SA')} من {questions.length.toLocaleString('ar-SA')}</span></header>
          <div className="meeting-conversation-history">
            <div className="meeting-question"><span className="meeting-kicker">خالد · مسؤول التوظيف</span><h2>{original}</h2><p><strong>بكلمات أبسط: </strong>{simple}</p></div>
            {approved !== null && <div className="meeting-approved-message"><span className="meeting-kicker">{candidateName} · المرشح</span><p>{approved}</p><span className="meeting-protection"><Check className="size-4" />إجابة معتمدة · وصلت لمسؤول التوظيف</span></div>}
          </div>
          <div className="meeting-answer"><div className="meeting-answer-label"><label htmlFor="meeting-draft">{review ? 'الترجمة التجريبية · بانتظار تأكيدك' : 'أنا · المرشح'}</label><span><Clock3 className="size-3.5" />{answerSeconds === 0 ? 'يمكنك المتابعة' : `${answerSeconds.toLocaleString('ar-SA')} ثانية · عداد توضيحي`}</span></div>
            {approved === null ? <><Textarea id="meeting-draft" value={draft} onChange={event => { setDraft(event.target.value); setReview(false); }} rows={3} placeholder="اكتب رسالتك بصفتك المرشح…" />
              <div className="meeting-answer-actions"><Button className="meeting-primary" disabled={!connected || !draft.trim() || translating} onClick={review ? sendApproved : () => setReview(true)}>{review ? <Check /> : <ShieldCheck />}{review ? 'تأكيد وإرسال' : 'مراجعة الإجابة'}</Button>{review && <Button className="meeting-outline" onClick={() => setReview(false)}><Pencil />تعديل</Button>}<Button className="meeting-outline" disabled={!connected || translating} onClick={() => setTranslating(true)}>{translating ? <LoaderCircle className="animate-spin" /> : <RotateCcw />}{translating ? 'جارٍ المحاكاة…' : 'محاكاة الترجمة'}</Button></div></> : <Button className="meeting-primary w-full" disabled={!connected || index >= questions.length - 1} onClick={nextQuestion}>السؤال التالي<ArrowLeft /></Button>}
            <p className="meeting-protection"><ShieldCheck className="size-4" />لا تُرسل الإجابة قبل موافقتك</p>
          </div>
        </section>}
      </section>}
      {view !== 'candidate' && <section className="meeting-side" aria-label="جهة مسؤول التوظيف"><div className="meeting-side-label"><h2>خالد · مسؤول التوظيف</h2><span className="text-xs text-meeting-muted">{job.company}</span></div>{video('recruiter')}<div className="meeting-question"><span className="meeting-kicker flex gap-2 items-center"><MessageSquareText className="size-4" />النص الناتج عن كلام مسؤول التوظيف</span><h2>{original}</h2><label htmlFor="recruiter-question" className="text-xs text-meeting-muted block mt-4 mb-2">سؤال مكتوب للمرشح · محاكاة الكلام</label><Textarea id="recruiter-question" className="bg-meeting-panel border-meeting-border text-meeting-text" rows={2} value={customQuestion} onChange={event => setCustomQuestion(event.target.value)} placeholder="اكتب سؤالًا…" /><Button className="meeting-outline mt-3" disabled={!customQuestion.trim() || !connected} onClick={() => { setPostedQuestion(customQuestion.trim()); setCustomQuestion(''); setApproved(null); setDraft(''); setReview(false); setAnswerSeconds(120); announce('وصل سؤال مكتوب جديد إلى المرشح.'); }}>إرسال السؤال<ArrowLeft /></Button></div><div className="meeting-answer"><h3 className="text-sm font-semibold flex items-center gap-2"><Check className="size-5 text-meeting-accent" />إجابة المرشح المعتمدة</h3><div data-testid="recruiter-approved-answer" aria-live="polite">{approved !== null ? <p className="recruiter-answer">{approved}</p> : <p className="text-sm text-meeting-muted mt-4">بانتظار موافقة المرشح. لا تظهر المسودات هنا.</p>}</div><div className="flex flex-wrap gap-2 mt-6"><Button className="meeting-outline" onClick={() => { setSender('recruiter'); setDialog('reactions'); }} disabled={!connected}><Smile />إرسال تفاعل تشجيعي</Button><Button className="meeting-primary" disabled={!connected || approved === null || index >= questions.length - 1} onClick={nextQuestion}>السؤال التالي<ArrowLeft /></Button></div><p className="text-xs text-meeting-muted mt-5">{answers.length.toLocaleString('ar-SA')} إجابات معتمدة في هذه المقابلة</p></div></section>}
    </div>
    <p className="text-xs text-meeting-muted mt-3">طريقة التواصل: {({ sign: 'لغة الإشارة', text: 'الكتابة' })[communication]} · الكاميرا معاينة محلية فقط؛ لا تُسجَّل ولا تُرسل. النصوص محاكاة؛ تحويل كلام مسؤول التوظيف إلى لغة الإشارة والاتصال به غير متصلة.</p><footer className="meeting-toolbar"><div className="meeting-tools"><Tool label={media.camera ? 'إيقاف الكاميرا' : 'تشغيل الكاميرا'} pressed={media.camera} onClick={media.toggleCamera}>{media.busy ? <LoaderCircle className="animate-spin" /> : media.camera ? <Video /> : <VideoOff />}</Tool><Tool label="المحادثة والترجمة" pressed={conversationOpen} onClick={() => setConversationOpen(current => !current)}><MessageSquareText /></Tool><Tool label="عرض نص السؤال على الفيديو" pressed={captions} onClick={() => setCaptions(current => !current)}><Captions /></Tool><Tool label="التفاعلات التشجيعية" onClick={() => { setSender(view === 'recruiter' ? 'recruiter' : 'candidate'); setDialog('reactions'); }}><Smile /></Tool>{view !== 'candidate' && <Tool label="عرض الجهازين" onClick={() => setDialog('devices')}><MonitorSmartphone /></Tool>}<Tool label="التنبيهات والاتصال" onClick={() => setDialog('settings')}><Settings2 /></Tool></div><div className="flex items-center gap-3"><p className="text-xs text-meeting-muted flex items-center gap-1">{connected ? <Wifi className="size-4" /> : <WifiOff className="size-4" />}{connected ? 'اتصال تجريبي' : 'غير متصل'}</p><Button variant="destructive" onClick={() => setDialog('end')}><PhoneOff />إنهاء المقابلة</Button></div></footer>
    <Dialog open={dialog !== null} onOpenChange={open => { if (!open) setDialog(null); }}><DialogContent dir="rtl">
      {dialog === 'reactions' && <><DialogTitle>التفاعلات التشجيعية</DialogTitle><DialogDescription>يصل التفاعل إلى الطرف الآخر فورًا في المحاكاة.</DialogDescription><div className="flex gap-2" role="group" aria-label="مرسل التفاعل"><Button variant={sender === 'recruiter' ? 'secondary' : 'ghost'} aria-pressed={sender === 'recruiter'} onClick={() => setSender('recruiter')}>مسؤول التوظيف</Button><Button variant={sender === 'candidate' ? 'secondary' : 'ghost'} aria-pressed={sender === 'candidate'} onClick={() => setSender('candidate')}>المرشح</Button></div><div className="reaction-list">{reactions.map(item => <Button key={item.id} variant="outline" className="reaction-choice" aria-label={`${item.symbol} ${item.label}`} onClick={() => sendReaction(item)}><span aria-hidden="true">{item.symbol}</span><span>{item.label}</span></Button>)}</div></>}
      {dialog === 'devices' && <><DialogTitle>تجربة الجهازين</DialogTitle><DialogDescription>تبديل عرض المرشح ومسؤول التوظيف أو عرض الشاشتين معًا؛ لا يوجد ربط حقيقي بين أجهزة.</DialogDescription><MonitorSmartphone className="size-12 text-primary mx-auto" /><Button onClick={() => { setLinked(true); setView('both'); }}><Check />{linked ? 'الشاشتان متصلتان تجريبيًا' : 'محاكاة ربط الجهاز الثاني'}</Button><Button variant="outline" onClick={() => { setView('both'); setDialog(null); }}>عرض الشاشتين</Button></>}
      {dialog === 'settings' && <><DialogTitle>التنبيهات والاتصال</DialogTitle><DialogDescription>حالات مرئية لا تعتمد على الصوت.</DialogDescription><label className="flex justify-between gap-4 items-center text-sm min-h-12">إشعارات مرئية اختيارية<Switch checked={notifications} onCheckedChange={setNotifications} /></label><label className="flex justify-between gap-4 items-center text-sm min-h-12">اهتزاز في الأجهزة المدعومة<Switch checked={haptic} onCheckedChange={setHaptic} /></label><p className="text-xs text-muted-foreground">تنبيه الاتصال يبقى ظاهرًا دائمًا.</p><Button variant="outline" onClick={() => { setConnected(!connected); announce(connected ? 'انقطع الاتصال التجريبي.' : 'تمت استعادة الاتصال التجريبي.'); }}>{connected ? <WifiOff /> : <Wifi />}{connected ? 'محاكاة انقطاع الاتصال' : 'استعادة الاتصال'}</Button></>}
      {dialog === 'end' && <><DialogTitle>هل تريد إنهاء المقابلة؟</DialogTitle><DialogDescription>{preview ? 'لن تغيّر التجربة حالة الطلب أو التقارير. تتوقف الكاميرا عند المغادرة.' : 'يحفظ التقرير الإجابات المعتمدة فقط. لا تدخل المسودات أو التفاعلات في الإجابات.'}</DialogDescription><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => setDialog(null)}>متابعة المقابلة</Button><Button asChild>{preview ? <Link to="/dashboard">إنهاء التجربة والعودة<ArrowLeft /></Link> : <Link to="/report" onClick={() => state.finishInterview(approvedQuestions, seconds)}>إنهاء وعرض التقرير<ArrowLeft /></Link>}</Button></div></>}
    </DialogContent></Dialog>
  </section>;
}
function Tool({ label, pressed, onClick, children }: { label: string; pressed?: boolean; onClick: () => void; children: React.ReactNode }) {
  return <Tooltip><TooltipTrigger asChild><Button size="icon" variant="ghost" className="meeting-tool" aria-label={label} aria-pressed={pressed} onClick={onClick}>{children}</Button></TooltipTrigger><TooltipContent>{label}</TooltipContent></Tooltip>;
}