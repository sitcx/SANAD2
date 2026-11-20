import { useState } from 'react';
import { BriefcaseBusiness, Check, ClipboardCheck, Copy, FilePenLine, Mail, MessageSquareText, Quote, RefreshCw, Target, UserRound } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { dailySkills, nextDailySkillIndex, type DailySkillIcon } from '@/lib/daily-skills';

const skillIcons = {
  introduction: UserRound,
  application: FilePenLine,
  achievement: BriefcaseBusiness,
  clarification: ClipboardCheck,
  communication: MessageSquareText,
  followup: Mail,
} satisfies Record<DailySkillIcon, typeof UserRound>;

export function DailySkillCard() {
  const [skillIndex, setSkillIndex] = useState(0);
  const [copyStatus, setCopyStatus] = useState<'idle' | 'copied' | 'error'>('idle');
  const skill = dailySkills[skillIndex];
  if (!skill) return null;
  const SkillIcon = skillIcons[skill.icon];
  async function copyExample() {
    if (!skill) return;
    try {
      await navigator.clipboard.writeText(skill.example);
      setCopyStatus('copied');
    } catch {
      setCopyStatus('error');
    }
  }

  return <section className="workspace-section daily-skill-card" aria-labelledby="daily-skill-title">
    <div className="section-title"><h2 id="daily-skill-title"><Target aria-hidden="true" />مهارة اليوم</h2></div>
    <div className="daily-skill-content" aria-live="polite" aria-atomic="true">
      <div className="daily-skill-intro">
        <div className="min-w-0">
          <p className="daily-skill-category">{skill.category}</p>
          <h3 className="daily-skill-heading"><span className="daily-skill-heading-icon"><SkillIcon aria-hidden="true" /></span>{skill.title}</h3>
          <p className="daily-skill-description">{skill.description}</p>
        </div>
        <div className="daily-skill-illustration" aria-hidden="true">
          <span className="daily-skill-visual-lines"><i /><i /><i /></span>
          <SkillIcon className="daily-skill-symbol" strokeWidth={1.4} />
          <span className="daily-skill-detail"><BriefcaseBusiness strokeWidth={1.6} /></span>
        </div>
      </div>
      <div className="daily-skill-example">
        <h4><Quote aria-hidden="true" />مثال</h4>
        <blockquote>{skill.example}</blockquote>
      </div>
      <div className="daily-skill-actions">
        <Button variant="outline" onClick={() => { setSkillIndex(nextDailySkillIndex); setCopyStatus('idle'); }}><RefreshCw aria-hidden="true" />مهارة أخرى</Button>
        <Button onClick={copyExample}>{copyStatus === 'copied' ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}{copyStatus === 'copied' ? 'تم النسخ' : 'نسخ المثال'}</Button>
      </div>
      {copyStatus === 'error' && <p role="status" className="daily-skill-copy-error">لم يتم النسخ. يمكنك تحديد المثال ونسخه.</p>}
    </div>
  </section>;
}