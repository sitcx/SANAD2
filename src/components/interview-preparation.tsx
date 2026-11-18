import { ArrowLeft, Camera, Hand, Keyboard, LoaderCircle, UserRound, VideoOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { LocalMedia } from '@/hooks/use-local-media';
import { formatInterviewDate, type Job } from '@/lib/sanad-data';

export type InterviewCommunication = 'sign' | 'text';
export const interviewCommunicationChoices = [
  { id: 'sign', label: 'لغة الإشارة', Icon: Hand },
  { id: 'text', label: 'الكتابة', Icon: Keyboard },
] as const;

export function InterviewPreparation({ media, name, setName, communication, setCommunication, job, schedule, preview, onJoin }: {
  media: LocalMedia; name: string; setName: (name: string) => void;
  communication: InterviewCommunication; setCommunication: (value: InterviewCommunication) => void;
  job: Job; schedule: string | undefined; preview: boolean; onJoin: () => void;
}) {
  return <section className="interview-preparation" aria-labelledby="preparation-title">
    <div className="preparation-camera-column"><h2 id="preparation-title" className="text-2xl font-semibold mb-5">تجربة الكاميرا</h2>
      <div className="preparation-camera" aria-label="معاينة كاميرا المرشح">
        <video ref={media.videoRef} autoPlay playsInline muted className={media.camera ? 'local-camera' : 'local-camera hidden'} aria-label="معاينة الكاميرا المحلية" />
        {!media.camera && <div className="preparation-placeholder"><Camera className="size-12 text-meeting-accent" /><p>الكاميرا متوقفة</p><Button className="meeting-primary" disabled={media.busy} onClick={media.toggleCamera}>{media.busy ? <LoaderCircle className="animate-spin" /> : <Camera />}تشغيل الكاميرا</Button></div>}
        <span className="local-preview-tag">معاينة محلية · دون تسجيل</span>
        <div className="meeting-video-caption"><span className="flex gap-2 items-center"><UserRound className="size-4" />{name.trim() || 'المرشح'} · المرشح</span><span className="flex gap-1 items-center"><Hand className="size-4" />لغة الإشارة والكتابة</span></div>
      </div>
      <div className="flex flex-wrap gap-2 mt-3"><Button variant="outline" disabled={media.busy} onClick={media.toggleCamera}>{media.camera ? <VideoOff /> : <Camera />}{media.camera ? 'إيقاف الكاميرا' : 'تشغيل الكاميرا'}</Button></div>
      {media.error && <p role="alert" className="text-sm text-destructive mt-3">{media.error}</p>}
      <p className="text-xs text-muted-foreground mt-4">الكاميرا محلية فقط؛ دون تسجيل أو إرسال. لا يُستخدم الميكروفون لأن التواصل يتم بلغة الإشارة والكتابة.</p>
    </div>
    <div className="preparation-options"><label htmlFor="interview-name" className="block text-sm font-medium mb-2">اسمك</label><Input id="interview-name" value={name} onChange={event => setName(event.target.value)} autoComplete="off" />
      <div className="mt-5 text-sm"><p className="text-muted-foreground">المقابلة</p><p className="font-medium mt-1">{job.title} · {job.company}</p>{!preview && schedule && <p className="mt-2">{formatInterviewDate(schedule)} · بتوقيت الرياض</p>}</div>
      <fieldset className="mt-6"><legend className="text-sm font-medium mb-3">طريقة تواصلك المفضلة</legend><div className="preparation-communication">{interviewCommunicationChoices.map(({ id, label, Icon }) => <Button key={id} variant="outline" className="preparation-choice" aria-pressed={communication === id} onClick={() => setCommunication(id)}><span className="preparation-choice-icon"><Icon /></span>{label}</Button>)}</div></fieldset>
      <Button size="lg" className="w-full mt-6" disabled={!name.trim()} onClick={onJoin}>{preview ? 'ابدأ تجربة المقابلة' : 'انضم إلى المقابلة'}<ArrowLeft /></Button>
      <p className="text-xs text-muted-foreground mt-3">{preview ? 'دخول تجريبي · لا يغيّر طلبك أو تقاريرك.' : 'جلسة محاكاة · لا يوجد اتصال بجهة توظيف حقيقية.'}</p>
      <p className="text-xs text-muted-foreground mt-2">ترجمة لغة الإشارة غير متصلة في هذا النموذج.</p>
    </div>
  </section>;
}
