import { createFileRoute, Link } from '@tanstack/react-router';
import { Clock3, Video } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { MeetingRoom } from '@/components/meeting-room';
import { InterviewPreparation, type InterviewCommunication } from '@/components/interview-preparation';
import { useLocalMedia } from '@/hooks/use-local-media';
import { useSanad } from '@/lib/sanad-context';
import { canOpenInterview, formatInterviewDate, jobs, remainingTime } from '@/lib/sanad-data';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/interview')({ head: () => pageHead('غرفة المقابلة المباشرة', 'غرفة مقابلة بلغة الإشارة والكتابة، مع معاينة محلية للكاميرا، وأسئلة مكتوبة وإجابات يراجعها المرشح قبل اعتمادها.'), validateSearch: (search: Record<string, unknown>): { preview?: boolean } => ({ preview: search['preview'] === true || search['preview'] === 'true' }), component: Interview });
function Interview() {
  const preview = Route.useSearch().preview === true;
  const state = useSanad(); const job = jobs.find(item => item.id === state.selectedJobId) ?? jobs[0]; const [started, setStarted] = useState(false);
  const media = useLocalMedia();
  const [name, setName] = useState(state.candidateName);
  const [communication, setCommunication] = useState<InterviewCommunication>('sign');
  const schedule = state.schedules[job.id];
  const allowed = canOpenInterview(state.applications[job.id] ?? 'available', schedule, state.now, preview);
  if (!allowed) return <Workspace><PageTitle title="المقابلة المباشرة" subtitle={`${job.title} · ${job.company}`} /><section className="workspace-section"><Clock3 className="size-9 text-primary" /><h2 className="text-xl font-semibold mt-4">{state.applications[job.id] === 'nominated' ? 'مقابلتك في موعدها' : 'الدخول غير متاح حاليًا'}</h2><p className="text-sm text-muted-foreground mt-3">{schedule && state.applications[job.id] === 'nominated' ? `${formatInterviewDate(schedule)} · ${remainingTime(schedule, state.now)}` : 'يتاح الدخول بعد الترشيح وعند حلول الموعد، وقبل اكتمال المقابلة.'}</p><Button asChild className="mt-5"><Link to="/interview" search={{ preview: true }}><Video />تجربة المقابلة والكاميرا الآن</Link></Button><p className="text-xs text-muted-foreground mt-3">تجربة منفصلة عن المقابلة المجدولة، دون تغيير حالة الطلب.</p><div className="flex flex-wrap gap-3 mt-5"><Button asChild variant="outline"><Link to="/dashboard">تقويم المقابلات</Link></Button><Button asChild variant="outline"><Link to="/applications">تتبع تقديماتي</Link></Button><Button asChild variant="outline"><Link to="/coach">متابعة التدريب</Link></Button></div></section></Workspace>;
  if (started) return <MeetingRoom key={`${job.id}-${preview}`} job={job} preview={preview} media={media} candidateName={name.trim()} communication={communication} />;
  return <Workspace><PageTitle title={preview ? 'تجربة المقابلة' : 'المقابلة المباشرة'} subtitle={`${job.title} · ${job.company}`} /><InterviewPreparation media={media} name={name} setName={setName} communication={communication} setCommunication={setCommunication} job={job} schedule={schedule} preview={preview} onJoin={() => setStarted(true)} /></Workspace>;
}