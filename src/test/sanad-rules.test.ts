import { describe, expect, it } from 'vitest';
import { applicationSteps, approveAnswer, canJoinInterview, canOpenInterview, canUpdateApplication, communicationPreferences, getJobMatch, getReadiness, interviewSchedules, jobs, matchesRegion, reactionRecipient, requestInterpreter, riyadhDay, scheduleConflict, validateCvFile } from '@/lib/sanad-data';
import { calendarContent } from '@/lib/calendar-export';

describe('Candidate protection rules', () => {
  it('never sends a translated answer without candidate approval', () => {
    expect(approveAnswer('حللت بيانات المبيعات', false)).toBeNull();
    expect(approveAnswer('حللت بيانات المبيعات', true)).toBe('حللت بيانات المبيعات');
    expect(approveAnswer('   ', true)).toBeNull();
  });
  it('keeps a backup interpreter optional unless requested', () => {
    expect(requestInterpreter(false)).toBe('optional');
    expect(requestInterpreter(true)).toBe('requested');
  });
  it('shows the specified 95 percent match for the analyst accommodation plan', () => {
    expect(jobs.find(job => job.id === 'analyst')?.match).toBe(95);
  });
});

describe('Candidate journey rules', () => {
  const startsAt = '2026-11-17T10:00:00+03:00';
  it('allows entry only once the scheduled interview starts', () => {
    expect(canJoinInterview('nominated', startsAt, Date.parse('2026-11-17T09:59:59+03:00'))).toBe(false);
    expect(canJoinInterview('nominated', startsAt, Date.parse('2026-11-17T10:00:00+03:00'))).toBe(true);
  });
  it('requires nomination, not just an available job or an application', () => {
    const now = Date.parse('2026-11-17T10:30:00+03:00');
    expect(canJoinInterview('available', startsAt, now)).toBe(false);
    expect(canJoinInterview('applied', startsAt, now)).toBe(false);
    expect(canJoinInterview('nominated', startsAt, now)).toBe(true);
  });
  it('does not allow entry with an unknown clock or missing schedule', () => {
    expect(canJoinInterview('nominated', startsAt, undefined)).toBe(false);
    expect(canJoinInterview('nominated', undefined, Date.now())).toBe(false);
    expect(canJoinInterview('nominated', 'invalid', Date.now())).toBe(false);
  });
  it('shows job recommendations only after CV analysis', () => {
    expect(getJobMatch(jobs[0], 'uploaded')).toBeNull();
    expect(getJobMatch(jobs[0], 'analysing')).toBeNull();
    expect(getJobMatch(jobs[0], 'analysed')).toBe(95);
  });
  it('calculates readiness from completed and remaining steps', () => {
    expect(getReadiness([true, true, false, true, false, false])).toBe(50);
    expect(getReadiness([true, true, true, true, true, true])).toBe(100);
    expect(getReadiness([false, false, false, false, false, false])).toBe(0);
  });
  it('accepts PDF and Word CV files within the ten megabyte limit', () => {
    expect(validateCvFile('cv.pdf', 10 * 1024 * 1024)).toBeNull();
    expect(validateCvFile('cv.doc', 1024)).toBeNull();
    expect(validateCvFile('cv.docx', 1024)).toBeNull();
    expect(validateCvFile('cv.pdf', 10 * 1024 * 1024 + 1)).not.toBeNull();
    expect(validateCvFile('cv.exe', 1024)).not.toBeNull();
    expect(validateCvFile('cv.pdf', 0)).not.toBeNull();
  });
});

describe('Final prototype rules', () => {
  it('tracks the expanded application outcomes while retaining completed interviews', () => {
    expect(applicationSteps).toEqual(['applied', 'reviewing', 'nominated', 'scheduled', 'completed', 'accepted', 'rejected', 'withdrawn']);
    expect(canUpdateApplication('applied', 'reviewing')).toBe(true);
    expect(canUpdateApplication('reviewing', 'nominated')).toBe(true);
    expect(canUpdateApplication('nominated', 'completed')).toBe(true);
    expect(canUpdateApplication('completed', 'accepted')).toBe(true);
    expect(canUpdateApplication('completed', 'rejected')).toBe(true);
    expect(canUpdateApplication('available', 'accepted')).toBe(false);
    expect(canUpdateApplication('accepted', 'nominated')).toBe(false);
  });
  it('sends recruiter reactions to the candidate and candidate reactions to the recruiter', () => {
    expect(reactionRecipient('recruiter')).toBe('candidate');
    expect(reactionRecipient('candidate')).toBe('recruiter');
  });
  it('exports the selected interview time with a visual calendar reminder', () => {
    const content = calendarContent(jobs[0], '2026-11-17T10:00:00+03:00');
    expect(content).toContain('DTSTART:20261117T070000Z');
    expect(content).toContain('DTEND:20261117T073000Z');
    expect(content).toContain('ACTION:DISPLAY');
  });
});

describe('November review rules', () => {
  it('never places two fixture interviews on the same Riyadh day', () => {
    const days = Object.values(interviewSchedules).map(riyadhDay);
    expect(new Set(days).size).toBe(3);
  });
  it('rejects another interview on the same Riyadh day even across UTC midnight', () => {
    expect(scheduleConflict('support', '2026-11-19T22:00:00Z', interviewSchedules)).not.toBeNull();
    expect(scheduleConflict('support', '2026-11-19T11:00:00+03:00', interviewSchedules)).toBeNull();
  });
  it('allows rescheduling the same interview on its own day', () => {
    expect(scheduleConflict('analyst', '2026-11-20T11:00:00+03:00', interviewSchedules)).toBeNull();
  });
  it('places the scheduled fixture interviews on Friday 20 and Sunday 22 November', () => {
    const weekday = (value: string) => new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Riyadh', weekday: 'long' }).format(new Date(value));
    expect(riyadhDay(interviewSchedules['analyst'])).toBe('2026-11-20');
    expect(riyadhDay(interviewSchedules['support'])).toBe('2026-11-22');
    expect(weekday(interviewSchedules['analyst'])).toBe('Friday');
    expect(weekday(interviewSchedules['support'])).toBe('Sunday');
  });
  it('filters jobs by geographic region without treating remote work as Riyadh', () => {
    expect(jobs.filter(job => matchesRegion(job, 'الرياض')).map(job => job.id)).toEqual(['analyst']);
    expect(jobs.filter(job => matchesRegion(job, 'جدة')).map(job => job.id)).toEqual(['designer']);
    expect(jobs.filter(job => matchesRegion(job, 'remote')).map(job => job.id)).toEqual(['support']);
  });
  it('permits an explicit preview without nomination or a scheduled start', () => {
    expect(canOpenInterview('available', undefined, undefined, true)).toBe(true);
    expect(canOpenInterview('available', undefined, undefined, false)).toBe(false);
  });
  it('supports only the five requested communication methods', () => {
    expect(communicationPreferences.map(item => item.id)).toEqual(['sign', 'text', 'lip-reading', 'hearing-aid', 'other']);
  });
  it('names the sign-language method as an interpreter in the communication field', () => {
    const sign = communicationPreferences.find(item => item.id === 'sign');
    expect(sign?.label).toBe('مترجم لغة إشارة');
    const bare = 'لغة الإشارة' as string;
    expect(communicationPreferences.some(item => (item.label as string) === bare)).toBe(false);
  });
  it('supports scheduled interviews and candidate withdrawal', () => {
    expect(canUpdateApplication('reviewing', 'scheduled')).toBe(true);
    expect(canUpdateApplication('scheduled', 'withdrawn')).toBe(true);
    expect(canJoinInterview('withdrawn', interviewSchedules['analyst'], Date.parse('2026-11-20T11:00:00+03:00'))).toBe(false);
    expect(canJoinInterview('scheduled', interviewSchedules['analyst'], Date.parse('2026-11-20T11:00:00+03:00'))).toBe(true);
  });
});