import { Link } from '@tanstack/react-router';
import { ArrowLeft, CalendarDays, Check, Clock3, Download, Video } from 'lucide-react';
import { useState } from 'react';
import { arSA } from 'date-fns/locale';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { canJoinInterview, formatInterviewDate, riyadhDay, jobs, type Job } from '@/lib/sanad-data';
import { downloadCalendar } from '@/lib/calendar-export';
import { useSanad } from '@/lib/sanad-context';

function calendarDate(value: string) {
  const [year = 2026, month = 1, day = 1] = riyadhDay(value).split('-').map(Number);
  return new Date(year, month - 1, day);
}
export function InterviewCalendar({ empty = false }: { empty?: boolean } = {}) {
  const state = useSanad();
  const scheduled = empty ? [] : jobs.filter(job => ['nominated', 'scheduled'].includes(state.applications[job.id] ?? '')).sort((a, b) => Date.parse(state.schedules[a.id] ?? '') - Date.parse(state.schedules[b.id] ?? ''));
  const [selected, setSelected] = useState<Date>();
  const [open, setOpen] = useState(false);
  const dates = scheduled.flatMap(job => (state.schedules[job.id] ?? '') ? [calendarDate((state.schedules[job.id] ?? ''))] : []);
  const dayJobs = selected ? scheduled.filter(job => calendarDate((state.schedules[job.id] ?? '')).toDateString() === selected.toDateString()) : [];
  return <section aria-labelledby="calendar-title" className="workspace-section interview-calendar-section">
    <div className="section-title calendar-section-title"><h2 id="calendar-title"><CalendarDays />تقويم المقابلات</h2><span className="text-xs text-muted-foreground shrink-0">بتوقيت الرياض</span></div>
    <div className="calendar-month-area">
      <Calendar mode="single" dir="rtl" locale={arSA} numerals="arab" defaultMonth={new Date(2026, 10, 1)} selected={selected} onSelect={date => { setSelected(date); if (date) setOpen(true); }} modifiers={{ interview: dates }} modifiersClassNames={{ interview: 'calendar-interview' }} className="interview-calendar" />
      <p className="calendar-legend"><span className="size-2 rounded-full bg-primary shrink-0" />موعد مقابلة</p>
    </div>
    <div className="calendar-agenda" aria-labelledby="calendar-agenda-title">
      <div className="calendar-agenda-heading"><h3 id="calendar-agenda-title">مواعيد المقابلات</h3><span>{scheduled.length.toLocaleString('ar-SA')} مواعيد</span></div>
      {scheduled.length ? <div className="calendar-events">{scheduled.map(job => {
        const date = state.schedules[job.id] ?? '';
        const day = calendarDate(date);
        return <Button key={job.id} variant="ghost" className="calendar-event" onClick={() => { setSelected(day); setOpen(true); }}>
          <span className="calendar-event-date" aria-hidden="true"><span>{day.toLocaleDateString('ar-SA', { calendar: 'gregory', day: 'numeric' })}</span><span>{day.toLocaleDateString('ar-SA', { calendar: 'gregory', month: 'short' })}</span></span>
          <span className="calendar-event-copy"><span className="calendar-event-title">{job.title}</span><span className="calendar-event-company">{job.company}</span><span className="calendar-event-time"><Clock3 aria-hidden="true" /><span>{formatInterviewDate(date)}</span></span></span>
          <ArrowLeft className="calendar-event-arrow" aria-hidden="true" />
        </Button>;
      })}</div> : <p className="text-sm text-muted-foreground">لا توجد مقابلات مجدولة حاليًا.</p>}
    </div>
    <Dialog open={open} onOpenChange={setOpen}><DialogContent dir="rtl"><DialogTitle>تفاصيل مقابلات اليوم</DialogTitle><DialogDescription>{selected?.toLocaleDateString('ar-SA', { calendar: 'gregory', day: 'numeric', month: 'long', year: 'numeric' })} · بتوقيت الرياض</DialogDescription>
      {dayJobs.length ? dayJobs.map(job => <CalendarInterview key={job.id} job={job} close={() => setOpen(false)} />) : <p className="text-sm text-muted-foreground">لا توجد مقابلات في هذا اليوم.</p>}
    </DialogContent></Dialog>
  </section>;
}
function CalendarInterview({ job, close }: { job: Job; close: () => void }) {
  const state = useSanad();
  const [added, setAdded] = useState(false);
  const allowed = canJoinInterview(state.applications[job.id] ?? 'available', (state.schedules[job.id] ?? ''), state.now);
  return <div className="border-t border-border pt-4"><h3 className="font-semibold">{job.title}</h3><p className="text-sm text-muted-foreground">{job.company}</p><p className="flex gap-2 text-sm my-3"><Clock3 className="size-5 text-primary" />{formatInterviewDate((state.schedules[job.id] ?? ''))}</p><p className="text-xs text-muted-foreground mb-4">مقابلة مرئية مدعومة بالنص · موعد تجريبي · تذكير قبل ١٥ دقيقة</p><Button variant="outline" className="mb-4" onClick={() => { downloadCalendar(job, state.schedules[job.id] ?? ''); setAdded(true); }}>{added ? <Check /> : <Download />}{added ? 'تم تنزيل موعد المقابلة' : 'إضافة المقابلة إلى التقويم'}</Button><div className="flex flex-wrap gap-2"><Button asChild variant="outline"><Link to="/jobs/$jobId" params={{ jobId: job.id }} onClick={close}>تفاصيل الوظيفة والتهيئة</Link></Button>{allowed ? <Button asChild><Link to="/interview" onClick={() => { state.selectJob(job.id); close(); }}><Video />الدخول للمقابلة</Link></Button> : <Button disabled><Clock3 />الدخول عند حلول الموعد</Button>}</div></div>;
}