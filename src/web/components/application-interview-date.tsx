export function ApplicationInterviewDate({ value }: { value: string }) {
  const date = new Date(value);
  return <>
    <time dateTime={value} className="block">{date.toLocaleDateString('ar-SA', { calendar: 'gregory', timeZone: 'Asia/Riyadh', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</time>
    <span className="block">{date.toLocaleTimeString('ar-SA', { timeZone: 'Asia/Riyadh', hour: 'numeric', minute: '2-digit' })} · بتوقيت الرياض</span>
  </>;
}