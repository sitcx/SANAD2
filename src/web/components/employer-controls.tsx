import { useState } from 'react';
import { CalendarDays, Check, ClipboardCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useSanad } from '@/lib/sanad-context';
import { type Job } from '@/lib/sanad-data';
import { getSharedCommunicationNeeds } from '@/lib/communication-needs';

export function EmployerControls({ job }: { job: Job }) {
  const state = useSanad();
  const [date, setDate] = useState((state.schedules[job.id] ?? '').slice(0, 16));
  const [skills, setSkills] = useState((state.jobSkills[job.id] ?? job.skills).join('، '));
  const [message, setMessage] = useState('');
  const needs = getSharedCommunicationNeeds(state.preferences[job.id] ?? [], state.additionalCommunicationNeeds[job.id] ?? '');
  return <section className="workspace-section" aria-labelledby="employer-title"><div className="section-title"><h2 id="employer-title"><ClipboardCheck />إعدادات الشركة · محاكاة</h2></div><p className="text-sm text-muted-foreground mb-5">إعداد الوظيفة والمقابلة للمرشح {state.candidateName}، دون إرسال إلى شركة حقيقية.</p><h3 className="font-semibold text-sm mb-3">تسهيلات المرشح</h3>
    {needs.length > 0 ? <ul className="grid gap-4 mb-5">{needs.map(item => <li key={item.id} className="border-s-2 border-primary ps-3"><h4 className="font-semibold text-sm">{item.label}</h4><p className="text-sm text-muted-foreground leading-loose mt-1">{item.description}</p>{item.additionalNeeds && <p className="text-sm mt-2 whitespace-pre-wrap break-words">{item.additionalNeeds}</p>}</li>)}</ul> : <p className="text-sm text-muted-foreground mb-5">لم يحدد المرشح تفضيلات التواصل بعد.</p>}
    <form className="grid gap-5 sm:grid-cols-2" onSubmit={event => { event.preventDefault(); if (!date || !skills.trim()) return; const error = state.scheduleInterview(job.id, `${date}:00+03:00`); if (error) { setMessage(error); return; } state.setJobSkills(job.id, skills.split(/[،,]/).map(item => item.trim()).filter(Boolean)); setMessage('تم تحديث المهارات وموعد المقابلة تجريبيًا.'); }}><div><label htmlFor="employer-skills" className="block font-semibold text-sm mb-2">المهارات المطلوبة</label><Input id="employer-skills" required value={skills} onChange={event => setSkills(event.target.value)} /></div><div><label htmlFor="employer-date" className="block font-semibold text-sm mb-2">موعد المقابلة · بتوقيت الرياض</label><Input id="employer-date" type="datetime-local" required dir="ltr" value={date} onChange={event => setDate(event.target.value)} /></div><div className="sm:col-span-2"><Button type="submit" variant="outline"><CalendarDays />حفظ إعدادات المقابلة</Button><p role="status" className="flex gap-2 text-primary text-sm mt-3">{message && <Check className="size-5" />}{message}</p></div></form></section>;
}