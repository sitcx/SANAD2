import { ArrowLeft, Bot, Camera, Hand, LoaderCircle, RotateCcw, UserRound, VideoOff } from 'lucide-react';
import { interpreterChoices, type InterpreterChoice } from '@/lib/sign-interpreter';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { LocalMedia } from '@/hooks/use-local-media';
import { formatInterviewDate, type Job } from '@/lib/sanad-data';

export function InterviewPreparation({ media, name, setName, interpreter, setInterpreter, job, schedule, preview, onJoin }: {
  media: LocalMedia; name: string; setName: (name: string) => void;
  interpreter: InterpreterChoice | null; setInterpreter: (value: InterpreterChoice | null) => void;
  job: Job; schedule: string | undefined; preview: boolean; onJoin: () => void;
}) {
  return <section className="interview-preparation" aria-labelledby="preparation-title">
    <div className="preparation-camera-column"><h2 id="preparation-title" className="text-2xl font-semibold mb-5">تجربة الكاميرا</h2>
      <div className="preparation-camera" aria-label="معاينة كاميرا المرشح">
        <video ref={media.videoRef} autoPlay playsInline muted className={media.camera ? 'local-camera' : 'local-camera hidden'} aria-label="معاينة الكاميرا المحلية" />
        {!media.camera && <div className="preparation-placeholder"><Camera className="size-12 text-meeting-accent" /><p>الكاميرا متوقفة</p><Button className="meeting-primary" disabled={media.busy} onClick={media.toggleCamera}>{media.busy ? <LoaderCircle className="animate-spin" /> : <Camera />}تشغيل الكاميرا</Button></div>}
        <span className="local-preview-tag">معاينة محلية · دون تسجيل</span>
        <div className="meeting-video-caption"><span className="flex gap-2 items-center"><UserRound className="size-4" />{name.trim() || 'المرشح'} · المرشح</span><span className="flex gap-1 items-center"><Hand className="size-4" />لغة الإشارة</span></div>
      </div>
      <div className="flex flex-wrap gap-2 mt-3"><Button variant="outline" disabled={media.busy} onClick={media.toggleCamera}>{media.camera ? <VideoOff /> : <Camera />}{media.camera ? 'إيقاف الكاميرا' : 'تشغيل الكاميرا'}</Button></div>
      {media.error && <p role="alert" className="text-sm text-destructive mt-3">{media.error}</p>}
      <p className="text-xs text-muted-foreground mt-4">الكاميرا محلية فقط؛ دون تسجيل أو إرسال. لا يُستخدم الميكروفون لأن تواصلك يتم بلغة الإشارة.</p>
    </div>
    <div className="preparation-options"><label htmlFor="interview-name" className="block text-sm font-medium mb-2">اسمك</label><Input id="interview-name" value={name} onChange={event => setName(event.target.value)} autoComplete="off" />
      <div className="mt-5 text-sm"><p className="text-muted-foreground">المقابلة</p><p className="font-medium mt-1">{job.title} · {job.company}</p>{!preview && schedule && <p className="mt-2">{formatInterviewDate(schedule)} · بتوقيت الرياض</p>}</div>
      <fieldset className="mt-6"><legend className="text-sm font-medium mb-3">اختر نوع المترجم قبل بدء المقابلة</legend><div className="preparation-communication">{interpreterChoices.map(({ id, label, description }) => <Button key={id} variant="outline" className="preparation-choice h-auto whitespace-normal" aria-pressed={interpreter === id} disabled={interpreter !== null && interpreter !== id} onClick={() => setInterpreter(id)}><span className="preparation-choice-icon">{id === 'ai' ? <Bot /> : <Hand />}</span><span className="grid gap-1 text-start"><span>{label}</span><span className="text-xs text-muted-foreground font-normal">{description}</span></span></Button>)}</div>
        {interpreter !== null && <Button variant="link" className="px-0 mt-2" onClick={() => setInterpreter(null)}><RotateCcw />تغيير الاختيار</Button>}</fieldset>
      <Button size="lg" className="w-full mt-6" disabled={!name.trim() || interpreter === null} onClick={onJoin}>{preview ? 'ابدأ تجربة المقابلة' : 'انضم إلى المقابلة'}<ArrowLeft /></Button>
      <p className="text-xs text-muted-foreground mt-3">{preview ? 'دخول تجريبي · لا يغيّر طلبك أو تقاريرك.' : 'جلسة محاكاة · لا يوجد اتصال بجهة توظيف حقيقية.'}</p>
      <p className="text-xs text-muted-foreground mt-2">بعد الاختيار يصبح الخيار الآخر غير متاح. في مترجم الذكاء الاصطناعي يمكنك طلب مترجم بشري في أي وقت.</p>
    </div>
  </section>;
}
