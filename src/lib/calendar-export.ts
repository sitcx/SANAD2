import type { Job } from './sanad-data';

export function calendarContent(job: Job, startsAt: string): string {
  const start = new Date(startsAt);
  const end = new Date(start.getTime() + 30 * 60 * 1000);
  const stamp = (date: Date) => date.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
  return ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Sanad//Interview//AR', 'BEGIN:VEVENT', `UID:sanad-${job.id}-${stamp(start)}`, `DTSTAMP:${stamp(start)}`, `DTSTART:${stamp(start)}`, `DTEND:${stamp(end)}`, `SUMMARY:مقابلة ${job.title} — ${job.company}`, 'DESCRIPTION:مقابلة تجريبية في سَند. راجع خطة التهيئة قبل الموعد.', 'BEGIN:VALARM', 'TRIGGER:-PT15M', 'ACTION:DISPLAY', 'DESCRIPTION:تذكير بالمقابلة بعد ١٥ دقيقة', 'END:VALARM', 'END:VEVENT', 'END:VCALENDAR'].join('\r\n');
}
export function downloadCalendar(job: Job, startsAt: string) {
  const url = URL.createObjectURL(new Blob([calendarContent(job, startsAt)], { type: 'text/calendar;charset=utf-8' }));
  const link = document.createElement('a'); link.href = url; link.download = `sanad-${job.id}.ics`; link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}