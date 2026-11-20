import { CalendarDays, Check, CheckCheck, ClipboardCheck, FileCheck2, Flag, Search, X } from 'lucide-react';
import { useMemo } from 'react';
import { useApplicationJourney } from '@/hooks/use-application-journey';
import { ApplicationInterviewDate } from '@/components/application-interview-date';
import { getApplicationProgress, type ApplicationEvent } from '@/lib/application-progress';
import { statusLabels, type ApplicationStatus } from '@/lib/sanad-data';

const icons = { available: FileCheck2, applied: FileCheck2, reviewing: Search, nominated: ClipboardCheck, scheduled: CalendarDays, completed: CheckCheck, accepted: Flag, rejected: X, withdrawn: X };
const labels = { completed: 'مكتملة', current: 'المرحلة الحالية', upcoming: 'قادمة', skipped: 'لم تمر بهذه المرحلة' };

export function ApplicationProgress({ status, history, paused = false, interviewAt = null }: { status: ApplicationStatus; history: readonly ApplicationEvent[]; paused?: boolean; interviewAt?: string | null }) {
  const progress = useMemo(() => getApplicationProgress(status, history), [status, history]);
  const journey = useApplicationJourney(progress, paused);
  const ended = status === 'accepted' || status === 'rejected' || status === 'withdrawn';
  return <ol ref={journey.ref} className="application-progress" aria-label="مراحل الطلب" data-settled={journey.settled}>
    {progress.map((step, index) => {
      const Icon = icons[step.status];
      const current = step.state === 'current';
      const phase = journey.steps[index] ?? { node: 'hidden', connector: 'hidden' };
      return <li key={step.status} className="application-progress-step" data-state={step.state} data-phase={phase.node} data-pulse={current && !ended && phase.node === 'active' && !paused} data-outcome={current && (step.status === 'rejected' || step.status === 'withdrawn')} aria-current={current ? 'step' : undefined}>
        <span className="application-progress-node" aria-hidden="true"><Icon />{step.state === 'completed' && <span className="application-progress-check"><Check /></span>}</span>
        <div className="application-progress-copy">
          <span className="application-progress-title">{statusLabels[step.status]}</span>
          <span className="application-progress-state">{current && ended ? 'نتيجة الطلب' : labels[step.state]}</span>
          {step.status === 'scheduled' && interviewAt ? <span className="application-progress-date"><ApplicationInterviewDate value={interviewAt} /></span> : step.date && <time dateTime={step.date} className="application-progress-date">{new Date(step.date).toLocaleDateString('ar-SA', { calendar: 'gregory', timeZone: 'Asia/Riyadh', day: 'numeric', month: 'short' })}</time>}
          {step.status === 'scheduled' && current && !interviewAt && <span className="application-progress-date">لم يُحدد الموعد بعد</span>}
        </div>
        {index < progress.length - 1 && <span className="application-progress-connector" data-connection={phase.connector} aria-hidden="true" />}
        <span className="sr-only">المرحلة {(index + 1).toLocaleString('ar-SA')}</span>
      </li>;
    })}
  </ol>;
}