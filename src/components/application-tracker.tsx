import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { ArrowLeft, ClipboardList } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useSanad } from '@/lib/sanad-context';
import { ApplicationProgress } from '@/components/application-progress';
import { ApplicationInterviewDate } from '@/components/application-interview-date';
import { getApplicationInterview } from '@/lib/application-interview';
import { applicationSteps, formatInterviewDate, jobs, nextSteps, statusLabels } from '@/lib/sanad-data';

export function ApplicationTracker({ compact = false }: { compact?: boolean }) {
  const state = useSanad();
  const [filter, setFilter] = useState('all');
  const all = jobs.filter(job => (state.applications[job.id] ?? 'available') !== 'available');
  const filtered = all.filter(job => filter === 'all' || state.applications[job.id] === filter);
  return <div data-compact={compact}>
    <div className="flex flex-wrap items-center justify-between gap-3 mb-5"><p className="text-sm text-muted-foreground">{all.length.toLocaleString('ar-SA')} طلبات · محاكاة في الجلسة الحالية</p><Select value={filter} onValueChange={setFilter} dir="rtl"><SelectTrigger className="w-52" aria-label="تصفية الطلبات حسب الحالة"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">جميع الحالات</SelectItem>{applicationSteps.map(status => <SelectItem key={status} value={status}>{statusLabels[status]}</SelectItem>)}</SelectContent></Select></div>
    <div className="space-y-4">{filtered.map(job => {
      const status = state.applications[job.id] ?? 'applied';
      const history = state.applicationHistory[job.id] ?? [];
      const appliedAt = state.applicationDates[job.id];
      const interviewAt = getApplicationInterview(status, state.schedules[job.id]);
      return <article className="tracking-row" key={job.id} aria-label={`طلب ${job.title}`}>
        <div className="flex flex-wrap justify-between items-start gap-3"><div><h3 className="font-semibold">{job.title}</h3><p className="text-sm text-muted-foreground mt-1">{job.company}</p></div><span className="status-label" data-status={status}>{statusLabels[status]}</span></div>
        <dl className="grid sm:grid-cols-2 gap-3 text-sm mt-4"><div><dt className="text-muted-foreground">تاريخ التقديم</dt><dd>{appliedAt ? formatInterviewDate(appliedAt) : 'غير متاح'}</dd></div><div><dt className="text-muted-foreground">الخطوة التالية</dt><dd>{nextSteps[status]}</dd></div>{['nominated', 'scheduled'].includes(status) && <div><dt className="text-muted-foreground">موعد المقابلة</dt><dd>{interviewAt ? <ApplicationInterviewDate value={interviewAt} /> : 'لم يُحدد الموعد بعد'}</dd></div>}</dl>
        <ApplicationProgress status={status} history={history} paused={state.guideOpen} interviewAt={interviewAt} />
        <div className="mt-5"><Button asChild variant="link" className="px-0"><Link to="/jobs/$jobId" params={{ jobId: job.id }}>تفاصيل الوظيفة<ArrowLeft /></Link></Button></div>
      </article>;
    })}</div>
    {!filtered.length && <div className="py-8 text-center"><ClipboardList className="size-7 mx-auto text-primary" /><p className="text-sm text-muted-foreground mt-3">لا توجد طلبات في هذه الحالة.</p><Button variant="outline" asChild className="mt-4"><Link to="/jobs">استكشف الوظائف<ArrowLeft /></Link></Button></div>}
  </div>;
}