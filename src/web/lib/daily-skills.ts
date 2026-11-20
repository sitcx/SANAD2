export type DailySkillIcon = 'introduction' | 'application' | 'achievement' | 'clarification' | 'communication' | 'followup';

export interface DailySkill {
  id: string;
  category: string;
  title: string;
  description: string;
  example: string;
  icon: DailySkillIcon;
}

export const dailySkills: readonly DailySkill[] = [
  {
    id: 'introduction',
    category: 'المقابلة الوظيفية',
    title: 'عرّف بنفسك',
    description: 'اذكر اسمك، ومجال عملك، ومهارة تتقنها.',
    example: 'أنا [اسمك]. أعمل في [مجالك]، وأجيد [مهارتك].',
    icon: 'introduction',
  },
  {
    id: 'application',
    category: 'التقديم على الوظائف',
    title: 'قدّم على وظيفة',
    description: 'اكتب اسم الوظيفة ومهارتك. أرفق سيرتك الذاتية.',
    example: 'مرحبًا، أريد التقديم على وظيفة [اسم الوظيفة]. أجيد [مهارتك]. هذه سيرتي الذاتية. شكرًا لكم.',
    icon: 'application',
  },
  {
    id: 'achievement',
    category: 'عرض خبراتك',
    title: 'اذكر إنجازك',
    description: 'اذكر عملًا أنجزته، وكيف ساعد فريقك.',
    example: 'رتّبت ملفات المشروع. أصبح الفريق يجد الملفات بسرعة.',
    icon: 'achievement',
  },
  {
    id: 'clarification',
    category: 'في العمل',
    title: 'تأكّد من المطلوب',
    description: 'اسأل عن المهمة وموعد تسليمها قبل أن تبدأ.',
    example: 'هل المطلوب ملخص من صفحة واحدة؟ وهل أرسله يوم الخميس؟',
    icon: 'clarification',
  },
  {
    id: 'communication',
    category: 'التواصل في العمل',
    title: 'اختر طريقة التواصل',
    description: 'أخبر فريقك بالطريقة التي تناسبك قبل الاجتماع.',
    example: 'أفضّل التواصل بالكتابة. أرسلوا لي نقاط الاجتماع قبل الموعد، من فضلكم.',
    icon: 'communication',
  },
  {
    id: 'followup',
    category: 'بعد المقابلة',
    title: 'اسأل عن طلبك',
    description: 'إذا تأخر الرد عن الموعد، اسأل برسالة قصيرة.',
    example: 'مرحبًا، قابلتكم لوظيفة [اسم الوظيفة] يوم [التاريخ]. هل يوجد جديد بخصوص طلبي؟ شكرًا لكم.',
    icon: 'followup',
  },
];

export function nextDailySkillIndex(currentIndex: number): number {
  return (currentIndex + 1) % dailySkills.length;
}