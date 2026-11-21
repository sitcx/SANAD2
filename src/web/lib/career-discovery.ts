import type { Job } from './sanad-data';

/** Optional career-path discovery: general interest questions mapped to career tracks. */
export type CareerTrackId = 'tech' | 'creative' | 'service' | 'business';

export const careerTracks: readonly { id: CareerTrackId; label: string; description: string; jobIds: Job['id'][] }[] = [
  { id: 'tech', label: 'التقنية والبيانات', description: 'تحليل البيانات وحل المشكلات بالأرقام والأنظمة.', jobIds: ['analyst'] },
  { id: 'creative', label: 'الفنون الإبداعية والتصميم', description: 'التصميم وبناء تجارب بصرية واضحة وجميلة.', jobIds: ['designer'] },
  { id: 'service', label: 'خدمة العملاء والتواصل', description: 'مساعدة الناس وحل مشكلاتهم عبر التواصل الكتابي.', jobIds: ['support'] },
  { id: 'business', label: 'الإدارة والأعمال', description: 'التنظيم والتخطيط ومتابعة الإنجاز.', jobIds: ['analyst', 'support'] },
];

export const careerQuestions: readonly { id: string; question: string; options: readonly { track: CareerTrackId; label: string }[] }[] = [
  { id: 'activity', question: 'أي نشاط تستمتع به أكثر؟', options: [
    { track: 'tech', label: 'حل الألغاز والتعامل مع الأرقام' },
    { track: 'creative', label: 'الرسم والتصميم' },
    { track: 'service', label: 'مساعدة الآخرين' },
    { track: 'business', label: 'التنظيم والتخطيط' },
  ] },
  { id: 'team', question: 'في مشروع جماعي، أي دور تختار؟', options: [
    { track: 'tech', label: 'بناء الحل التقني' },
    { track: 'creative', label: 'تصميم الشكل والهوية' },
    { track: 'service', label: 'التواصل مع العملاء' },
    { track: 'business', label: 'توزيع المهام ومتابعتها' },
  ] },
  { id: 'tool', question: 'أي أداة ترغب في تعلّمها؟', options: [
    { track: 'tech', label: 'Excel وSQL' },
    { track: 'creative', label: 'Figma' },
    { track: 'service', label: 'أنظمة خدمة العملاء (CRM)' },
    { track: 'business', label: 'أدوات إدارة المشاريع' },
  ] },
  { id: 'achievement', question: 'ما الذي يشعرك بالإنجاز؟', options: [
    { track: 'tech', label: 'الوصول إلى نتيجة دقيقة' },
    { track: 'creative', label: 'فكرة جميلة يراها الناس' },
    { track: 'service', label: 'عميل راضٍ عن الخدمة' },
    { track: 'business', label: 'خطة نُفّذت بنجاح' },
  ] },
  { id: 'environment', question: 'أي بيئة عمل تناسبك؟', options: [
    { track: 'tech', label: 'تركيز وتحليل' },
    { track: 'creative', label: 'إبداع وحرية' },
    { track: 'service', label: 'تفاعل مع الناس' },
    { track: 'business', label: 'قيادة وتنظيم' },
  ] },
];

export interface CareerResult { track: (typeof careerTracks)[number]; percent: number }

/** Ranks tracks by the share of answers; ties keep the order of careerTracks. */
export function rankCareerTracks(answers: readonly CareerTrackId[]): CareerResult[] {
  const total = answers.length;
  return careerTracks
    .map(track => ({ track, percent: total ? Math.round(answers.filter(answer => answer === track.id).length / total * 100) : 0 }))
    .sort((a, b) => b.percent - a.percent);
}

export function careerTrackLabel(id: CareerTrackId | null): string | null {
  return careerTracks.find(track => track.id === id)?.label ?? null;
}
