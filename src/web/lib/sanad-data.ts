export const jobs = [
  { id: 'analyst', title: 'محلل بيانات', english: 'Data Analyst', company: 'شركة بُعد التقنية', mark: 'بُ', match: 95, location: 'الرياض', mode: 'هجين', salary: '٨٬٠٠٠ – ١٢٬٠٠٠ ر.س', description: 'حوّل البيانات إلى رؤى واضحة تساعد الفريق على اتخاذ قرارات أفضل.', skills: ['Excel', 'SQL', 'تحليل البيانات'], tone: 'teal' },
  { id: 'support', title: 'أخصائي دعم عملاء رقمي', english: 'Digital Customer Support', company: 'شركة وصال', mark: 'و', match: 92, location: 'عن بُعد', mode: 'عن بُعد', salary: '٦٬٠٠٠ – ٩٬٠٠٠ ر.س', description: 'ساعد العملاء عبر المحادثات المكتوبة والبريد الإلكتروني، وقدم حلولًا واضحة.', skills: ['التواصل الكتابي', 'حل المشكلات', 'CRM'], tone: 'lilac' },
  { id: 'designer', title: 'مصمم تجربة وواجهة مستخدم', english: 'UI/UX Designer', company: 'استوديو نقطة', mark: 'ن', match: 89, location: 'جدة', mode: 'هجين', salary: '٩٬٠٠٠ – ١٤٬٠٠٠ ر.س', description: 'صمّم تجارب رقمية سهلة الاستخدام تجعل المنتجات أكثر وضوحًا للجميع.', skills: ['Figma', 'بحث المستخدم', 'التصميم'], tone: 'peach' },
] as const;
export type Job = (typeof jobs)[number];
export const journeySteps = [
  { title: 'رفع السيرة الذاتية', detail: 'أضف سيرتك وخبراتك.' },
  { title: 'تحليل المهارات', detail: 'راجع مهاراتك وخبراتك.' },
  { title: 'ترشيح الوظائف', detail: 'اكتشف الوظائف المناسبة.' },
  { title: 'اختيار الوظيفة', detail: 'اطّلع على خطة التهيئة.' },
  { title: 'التدريب على المقابلة', detail: 'تدرّب على أسئلة واضحة.' },
  { title: 'المقابلة المباشرة', detail: 'تواصل بالمترجم الذكي.' },
];
export const coachQuestions = [
  { original: 'حدثنا عن نفسك وعن أبرز خبراتك المهنية.', simple: 'من أنت؟ وما المهارات والخبرات التي لديك؟' },
  { original: 'ما الذي جذبك إلى هذه الوظيفة؟', simple: 'لماذا تريد العمل في هذه الوظيفة؟' },
  { original: 'كيف تعاملت مع تحدٍ واجهك أثناء تحليل البيانات؟', simple: 'احكِ لنا عن مشكلة في عملك. كيف حللتها؟' },
  { original: 'كيف تضمن دقة النتائج التي تقدمها؟', simple: 'كيف تتأكد أن نتائج عملك صحيحة؟' },
  { original: 'كيف تتعاون مع أعضاء الفريق لتحقيق هدف مشترك؟', simple: 'كيف تعمل مع فريقك لإنجاز مهمة؟' },
  { original: 'ما هي أبرز نقاط قوتك المهنية؟', simple: 'ما الأشياء التي تجيدها في العمل؟' },
  { original: 'أين ترى نفسك مهنيًا خلال السنوات القادمة؟', simple: 'ما الذي تريد تعلمه أو تحقيقه في المستقبل؟' },
  { original: 'هل لديك أي أسئلة حول الفريق أو بيئة العمل؟', simple: 'ماذا تريد أن تعرف عن الشركة والعمل؟' },
] as const;
export const liveQuestions = [
  'حدثنا عن مشروع استخدمت فيه البيانات لحل مشكلة.',
  'كيف تتأكد من دقة البيانات قبل تحليلها؟',
  'كيف تتعاون مع فريقك لعرض النتائج؟',
];
export function approveAnswer(draft: string, approved: boolean): string | null {
  return approved && draft.trim().length > 0 ? draft.trim() : null;
}
export function requestInterpreter(requested: boolean): 'optional' | 'requested' {
  return requested ? 'requested' : 'optional';
}

export type ApplicationStatus = 'available' | 'applied' | 'reviewing' | 'nominated' | 'scheduled' | 'completed' | 'accepted' | 'rejected' | 'withdrawn';
export type CvStatus = 'uploaded' | 'analysing' | 'analysed';
export const statusLabels: Record<ApplicationStatus, string> = {
  available: 'متاحة للتقديم', applied: 'تم التقديم', reviewing: 'قيد المراجعة', nominated: 'تم الترشيح للمقابلة', scheduled: 'مقابلة مجدولة', completed: 'المقابلة مكتملة', accepted: 'عرض وظيفي', rejected: 'مرفوض', withdrawn: 'منسحب',
};
export const applicationSteps: ApplicationStatus[] = ['applied', 'reviewing', 'nominated', 'scheduled', 'completed', 'accepted', 'rejected', 'withdrawn'];
export const nextSteps: Record<ApplicationStatus, string> = {
  available: 'راجع التهيئة ثم قدّم طلبك.', applied: 'انتظر مراجعة الشركة لطلبك.', reviewing: 'ستظهر نتيجة مراجعة الطلب هنا.', nominated: 'راجع الموعد واستعد بالتدريب.', scheduled: 'راجع التقويم واستعد لموعد المقابلة.', completed: 'راجع التقرير وانتظر قرار الشركة.', accepted: 'تابع تفاصيل العرض مع الشركة.', rejected: 'اكتشف فرصًا أخرى مناسبة لمهاراتك.', withdrawn: 'تم الانسحاب من الطلب. يمكنك استكشاف وظائف أخرى.',
};
export function canUpdateApplication(current: ApplicationStatus, next: ApplicationStatus): boolean {
  const transitions: Record<ApplicationStatus, ApplicationStatus[]> = {
    available: ['applied'], applied: ['reviewing', 'nominated', 'scheduled', 'accepted', 'rejected', 'withdrawn'], reviewing: ['nominated', 'scheduled', 'accepted', 'rejected', 'withdrawn'], nominated: ['scheduled', 'completed', 'accepted', 'rejected', 'withdrawn'], scheduled: ['completed', 'accepted', 'rejected', 'withdrawn'], completed: ['accepted', 'rejected', 'withdrawn'], accepted: ['withdrawn'], rejected: [], withdrawn: [],
  };
  return transitions[current].includes(next);
}
export const interviewSchedules: Record<Job['id'], string> = {
  analyst: '2026-11-20T10:00:00+03:00',
  support: '2026-11-22T10:00:00+03:00',
  designer: '2026-11-27T10:00:00+03:00',
};
export const mockCvProfile = {
  skills: ['Excel', 'SQL', 'تحليل البيانات', 'التواصل الكتابي', 'حل المشكلات', 'CRM', 'Figma', 'بحث المستخدم', 'التصميم'],
  experience: ['تحليل المبيعات وإعداد التقارير · سنتان', 'مشروعات في الدعم الرقمي وتصميم واجهات الاستخدام'],
};
export const accommodationItems = [
  { id: 'questions', title: 'أسئلة مكتوبة وواضحة', detail: 'سؤال واحد في كل مرة، بالعربية المبسطة مع دعم لغة الإشارة عند توفره.' },
  { id: 'time', title: 'وقت كافٍ للمراجعة', detail: 'مراجعة الإجابة وتعديلها واعتمادها قبل مشاركتها مع الشركة.' },
  { id: 'video', title: 'اتصال مرئي مناسب', detail: 'إضاءة واضحة ومساحة لليدين والوجه، مع إمكانية استخدام جهاز ثانٍ.' },
  { id: 'followup', title: 'تواصل كتابي في العمل', detail: 'التقديم والمتابعة عبر البريد أو المحادثة، واجتماعات مدعومة بالنص.' },
] as const;
export interface InterviewReport {
  id: string;
  jobId: string;
  date: string;
  answers: string[];
  questions?: string[];
  durationSeconds?: number;
}
export const previousReports: InterviewReport[] = [{
  id: 'previous-analyst', jobId: 'analyst', date: '2026-11-10T10:00:00+03:00',
  answers: ['جمعت بيانات المبيعات ونظفتها باستخدام Excel، ثم حللتها باستخدام SQL لمساعدة الفريق على اتخاذ قرار أفضل.'],
}];
export function canJoinInterview(status: ApplicationStatus, startsAt: string | undefined, now: number | undefined): boolean {
  if (!['nominated', 'scheduled'].includes(status) || !startsAt || now === undefined) return false;
  const starts = Date.parse(startsAt);
  return Number.isFinite(starts) && now >= starts;
}
export function getJobMatch(job: Job, cvStatus: CvStatus): number | null {
  return cvStatus === 'analysed' ? job.match : null;
}
export function getReadiness(steps: boolean[]): number {
  return steps.length ? Math.round(steps.filter(Boolean).length / steps.length * 100) : 0;
}
export function validateCvFile(name: string, size: number): string | null {
  if (!/\.(pdf|doc|docx)$/i.test(name)) return 'اختر ملف PDF أو Word.';
  if (size > 10 * 1024 * 1024) return 'يرجى اختيار ملف أصغر من ١٠ ميجابايت.';
  if (size === 0) return 'الملف فارغ. اختر سيرة ذاتية أخرى.';
  return null;
}
export function formatInterviewDate(value: string): string {
  return new Date(value).toLocaleString('ar-SA', { calendar: 'gregory', timeZone: 'Asia/Riyadh', day: 'numeric', month: 'long', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}
export function remainingTime(startsAt: string, now: number | undefined): string {
  if (now === undefined) return 'جارٍ التحقق من الموعد…';
  const seconds = Math.max(0, Math.ceil((Date.parse(startsAt) - now) / 1000));
  if (!Number.isFinite(seconds)) return 'الموعد غير متاح';
  if (seconds === 0) return 'حان موعد المقابلة';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor(seconds % 86400 / 3600);
  const minutes = Math.floor(seconds % 3600 / 60);
  return `متبقي ${days ? `${days.toLocaleString('ar-SA')} يوم و` : ''}${hours.toLocaleString('ar-SA')} ساعة و${minutes.toLocaleString('ar-SA')} دقيقة`;
}
export const communicationPreferences = [
  { id: 'sign', label: 'مترجم لغة إشارة', description: 'أحتاج مترجمًا يتواصل معي بلغة الإشارة السعودية.' },
  { id: 'text', label: 'الكلام يظهر مكتوبًا', description: 'أريد ظهور كلام مسؤول التوظيف مكتوبًا أمامي أثناء المقابلة.' },
  { id: 'lip-reading', label: 'التحدث وجهًا لوجه', description: 'أفضّل رؤية وجه المتحدث وحركة شفتيه أثناء الكلام.' },
  { id: 'hearing-aid', label: 'استخدام السماعة الطبية', description: 'أستخدم سماعة طبية وأحتاج إلى صوت واضح أثناء المقابلة.' },
  { id: 'other', label: 'احتياج آخر', description: 'أستطيع كتابة أي متطلبات إضافية تساعدني على التواصل بشكل أفضل.' },
] as const;
export const liveQuestionSets: Record<Job['id'], { original: string; simple: string; answer: string }[]> = {
  analyst: liveQuestions.map((original, index) => ({ original, simple: ['احكِ عن مشروع حللت فيه البيانات. ما المشكلة؟ وكيف حللتها؟', 'كيف تتأكد أن البيانات صحيحة؟', 'كيف تشرح النتائج لفريقك؟'][index] ?? original, answer: ['نظفت بيانات المبيعات باستخدام Excel وحللتها باستخدام SQL. ساعدت النتائج الفريق على معرفة سبب تراجع المبيعات.', 'أراجع القيم الناقصة والمكررة وأقارن النتائج بالمصدر قبل إعداد التقرير.', 'أستخدم رسومًا واضحة وأشرح النتائج خطوة بخطوة، ثم أشارك تقريرًا مكتوبًا مع الفريق.'][index] ?? '' })),
  support: [
    { original: 'حدثنا عن موقف ساعدت فيه عميلًا على حل مشكلة.', simple: 'ما مشكلة العميل؟ وكيف ساعدته؟', answer: 'وصلتني رسالة من عميل لم يتمكن من متابعة طلبه. راجعت بياناته في CRM، وشرحت له الحل كتابةً، ثم تأكدت من حل المشكلة.' },
    { original: 'كيف تتعامل مع عدة طلبات دعم في وقت واحد؟', simple: 'كيف ترتب طلبات العملاء؟', answer: 'أرتب الطلبات حسب الأولوية ووقت الوصول، وأوثق الخطوات في نظام CRM وأبلغ العميل بوقت المتابعة.' },
    { original: 'كيف تتأكد أن العميل فهم الحل؟', simple: 'كيف تعرف أن الحل واضح للعميل؟', answer: 'أكتب خطوات قصيرة وواضحة، ثم أطلب من العميل تجربتها وأتابع معه عبر البريد الإلكتروني.' },
  ],
  designer: [
    { original: 'حدثنا عن تصميم حسّنت فيه تجربة المستخدم.', simple: 'ما الذي صممته؟ وكيف أصبح أسهل؟', answer: 'راجعت تجربة التسجيل وأجريت بحثًا مع المستخدمين، ثم بسّطت الخطوات وصممت واجهة واضحة في Figma.' },
    { original: 'كيف تختبر سهولة استخدام تصميمك؟', simple: 'كيف تتأكد أن التصميم سهل؟', answer: 'أطلب من المستخدمين تجربة مهام محددة وألاحظ الصعوبات، ثم أعدّل التصميم وأعيد الاختبار.' },
    { original: 'كيف تتعاون مع فريق التطوير؟', simple: 'كيف تشارك تصميمك مع المبرمجين؟', answer: 'أشارك النماذج والملاحظات في Figma، وأوضح حالات الواجهة وأراجع التنفيذ مع الفريق.' },
  ],
};
export const reactions = [
  { id: 'clap', symbol: '👏', label: 'أحسنت!' }, { id: 'stars', symbol: '⭐', label: 'إجابة رائعة!' }, { id: 'like', symbol: '👍', label: 'ممتاز!' }, { id: 'heart', symbol: '❤️', label: 'أحسنت يا أحمد!' }, { id: 'party', symbol: '🎉', label: 'رائع جدًا!' }, { id: 'strong', symbol: '💪', label: 'واصل، أنت مبدع!' }, { id: 'shine', symbol: '🌟', label: 'أداء مميز!' },
] as const;
export type MeetingSide = 'candidate' | 'recruiter';
export function reactionRecipient(sender: MeetingSide): MeetingSide { return sender === 'candidate' ? 'recruiter' : 'candidate'; }
export function riyadhDay(value: string): string {
  if (!Number.isFinite(Date.parse(value))) return '';
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Riyadh', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value));
}
export function scheduleConflict(id: string, value: string, schedules: Record<string, string>): string | null {
  const day = riyadhDay(value);
  if (!day) return 'اختر موعدًا صحيحًا.';
  return Object.entries(schedules).some(([otherId, date]) => otherId !== id && riyadhDay(date) === day) ? 'توجد مقابلة أخرى في هذا اليوم بتوقيت الرياض. اختر يومًا مختلفًا.' : null;
}
export function matchesRegion(job: Job, region: string): boolean {
  return region === 'all' || (region === 'remote' ? job.mode === 'عن بُعد' : job.location === region);
}
export function canOpenInterview(status: ApplicationStatus, startsAt: string | undefined, now: number | undefined, preview: boolean): boolean {
  return preview || canJoinInterview(status, startsAt, now);
}
