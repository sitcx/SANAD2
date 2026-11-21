import { canJoinInterview, formatInterviewDate, jobs, type ApplicationStatus, type CvStatus } from './sanad-data';

/** The single most useful next action for the candidate, from their real session state. */
export type NextStepKind = 'support' | 'offer' | 'interview-now' | 'interview-soon' | 'decision' | 'review' | 'cv' | 'apply';
export interface NextStep {
  kind: NextStepKind;
  title: string;
  text: string;
  action: string;
  to: '/support' | '/applications' | '/interview' | '/jobs' | '/dashboard';
  jobId?: string;
  preview?: boolean;
}

export function nextStep(input: { cvName: string; cvStatus: CvStatus; applications: Record<string, ApplicationStatus>; schedules: Record<string, string>; now: number | undefined }): NextStep {
  const { applications, schedules, now } = input;
  const withStatus = (...statuses: ApplicationStatus[]) => jobs.filter(job => statuses.includes(applications[job.id] ?? 'available'));

  const hired = withStatus('hired')[0];
  if (hired) return { kind: 'support', title: 'سند معك بعد التوظيف', text: `مبارك وظيفتك في ${hired.company}. إذا واجهت أي صعوبة، مثل الحاجة إلى مترجم أو تهيئة مستند، ارفع طلب دعم.`, action: 'رفع طلب دعم', to: '/support' };

  const offer = withStatus('accepted')[0];
  if (offer) return { kind: 'offer', title: 'وصلك عرض وظيفي', text: `قبلتك ${offer.company} في وظيفة ${offer.title}. اقبل العرض لتبدأ عملك.`, action: 'مراجعة العرض', to: '/applications' };

  const interviews = withStatus('nominated', 'scheduled')
    .filter(job => schedules[job.id])
    .sort((a, b) => Date.parse(schedules[a.id]!) - Date.parse(schedules[b.id]!));
  const ready = interviews.find(job => canJoinInterview(applications[job.id]!, schedules[job.id], now));
  if (ready) return { kind: 'interview-now', title: 'مقابلتك متاحة الآن', text: `حان موعد مقابلة ${ready.title} في ${ready.company}. ادخل الآن.`, action: 'دخول المقابلة', to: '/interview', jobId: ready.id };
  const upcoming = interviews[0];
  if (upcoming) return { kind: 'interview-soon', title: 'استعد لمقابلتك', text: `مقابلة ${upcoming.title} في ${upcoming.company} يوم ${formatInterviewDate(schedules[upcoming.id]!)}. جرّب الكاميرا وطريقة المقابلة قبل الموعد.`, action: 'تجربة المقابلة', to: '/interview', jobId: upcoming.id, preview: true };

  const waiting = withStatus('completed')[0];
  if (waiting) return { kind: 'decision', title: 'بانتظار قرار الجهة', text: `أكملت مقابلة ${waiting.title}. ستصلك النتيجة في تتبع طلباتك.`, action: 'تتبع طلباتي', to: '/applications' };

  const reviewing = withStatus('applied', 'reviewing')[0];
  if (reviewing) return { kind: 'review', title: 'طلبك قيد المراجعة', text: `تراجع ${reviewing.company} طلبك لوظيفة ${reviewing.title}. سنبلغك عند ترشيحك للمقابلة.`, action: 'تتبع طلباتي', to: '/applications' };

  if (!input.cvName || input.cvStatus !== 'analysed') return { kind: 'cv', title: 'ارفع سيرتك الذاتية', text: 'يستخرج سند مهاراتك من سيرتك، ثم يرشح لك الوظائف المناسبة مع نسبة التوافق.', action: 'إلى السيرة الذاتية', to: '/dashboard' };

  return { kind: 'apply', title: 'قدّم على وظيفة تناسبك', text: 'وظائف مرتبة حسب توافقها مع مهاراتك. اختر واحدة وقدّم عليها.', action: 'استعراض الوظائف', to: '/jobs' };
}
