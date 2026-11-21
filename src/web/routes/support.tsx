import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, Check, LifeBuoy, LoaderCircle, Mic, Send, Star } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { SpeakButton } from '@/components/speak-button';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { useSanad } from '@/lib/sanad-context';
import { formatInterviewDate, jobs } from '@/lib/sanad-data';
import { categoriesFor, supportCategories, ticketStatusLabels, ticketSteps, type SupportCategory } from '@/lib/support-tickets';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/support')({ head: () => pageHead('دعم سند بعد التوظيف', 'ارفع طلب دعم عند أي صعوبة في عملك، مثل مترجم إشارة أو تهيئة مستند للقراءة الصوتية، وتابع حالته حتى يُحل.'), component: Support });

type Recognition = { lang: string; onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null; onend: (() => void) | null; start: () => void };
function speechRecognition(): (new () => Recognition) | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

function Support() {
  const state = useSanad();
  const voice = state.communicationMode === 'voice';
  const categories = categoriesFor(state.communicationMode);
  const [category, setCategory] = useState<SupportCategory>(categories[0]!.id);
  const [details, setDetails] = useState('');
  const [error, setError] = useState('');
  const [listening, setListening] = useState(false);
  const hiredJob = jobs.find(job => state.applications[job.id] === 'hired');

  if (!hiredJob) return <Workspace><PageTitle title="دعم سند بعد التوظيف" subtitle="يتاح الدعم بعد توظيفك عبر سند." /><section className="workspace-section"><LifeBuoy className="size-9 text-primary" /><p className="text-sm text-muted-foreground mt-4">عندما تقبل عرضًا وظيفيًا وتصبح حالتك «موظف»، يمكنك رفع طلبات الدعم من هنا.</p><Button asChild variant="outline" className="mt-5"><Link to="/applications">تتبع تقديماتي<ArrowLeft /></Link></Button></section></Workspace>;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!details.trim()) return setError(voice ? 'صف مشكلتك بالكتابة أو بالصوت.' : 'صف مشكلتك بالكتابة.');
    if (state.submitSupportTicket(category, details)) { setDetails(''); setError(''); }
  }
  function dictate() {
    const Recognition = speechRecognition();
    if (!Recognition) return setError('الإدخال الصوتي غير مدعوم في هذا المتصفح.');
    const recognition = new Recognition();
    recognition.lang = 'ar-SA';
    recognition.onresult = event => setDetails(current => `${current} ${event.results[0]?.[0]?.transcript ?? ''}`.trim());
    recognition.onend = () => setListening(false);
    setListening(true); recognition.start();
  }

  return <Workspace><PageTitle title="دعم سند بعد التوظيف" subtitle={`${hiredJob.title} · ${hiredJob.company}. إذا واجهت صعوبة في عملك، ارفع طلبًا وسيتابعه فريق سند حتى يُحل.`} />
    <section className="workspace-section" aria-labelledby="new-ticket">
      <div className="section-title"><h2 id="new-ticket"><LifeBuoy />طلب دعم جديد</h2></div>
      <form onSubmit={submit} noValidate className="space-y-5">
        <fieldset><legend className="text-sm font-medium mb-3">نوع الطلب</legend><div className="grid sm:grid-cols-2 gap-3" role="radiogroup" aria-label="نوع الطلب">{categories.map(item => <Button key={item.id} type="button" variant="outline" role="radio" aria-checked={category === item.id} className="h-auto min-h-12 justify-start whitespace-normal text-start aria-checked:border-primary aria-checked:bg-secondary" onClick={() => setCategory(item.id)}>{category === item.id && <Check />}{item.label}</Button>)}</div></fieldset>
        <div><label htmlFor="ticket-details" className="block text-sm font-medium mb-2">صف المشكلة</label><Textarea id="ticket-details" rows={4} value={details} onChange={event => setDetails(event.target.value)} placeholder={voice ? 'اكتب أو استخدم الإدخال الصوتي…' : 'مثال: أحتاج مترجم إشارة لاجتماع الفريق يوم الأحد الساعة ١٠ صباحًا.'} /></div>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <div className="flex flex-wrap gap-3"><Button type="submit"><Send />إرسال الطلب</Button>{voice && <Button type="button" variant="outline" disabled={listening} onClick={dictate}>{listening ? <LoaderCircle className="animate-spin" /> : <Mic />}{listening ? 'جارٍ الاستماع…' : 'وصف المشكلة بالصوت'}</Button>}</div>
      </form>
    </section>
    <section className="workspace-section" aria-labelledby="my-tickets">
      <div className="section-title"><h2 id="my-tickets">طلباتي</h2><span className="text-xs text-muted-foreground">محاكاة: يتقدم الطلب تلقائيًا</span></div>
      {state.supportTickets.length === 0 ? <p className="text-sm text-muted-foreground">لا توجد طلبات بعد.</p> : <div className="space-y-4">{state.supportTickets.map(ticket => {
        const current = ticketSteps.indexOf(ticket.status);
        return <article key={ticket.id} className="tracking-row" aria-label={`طلب ${supportCategories.find(item => item.id === ticket.category)?.label}`}>
          <div className="flex flex-wrap justify-between items-start gap-3"><div><h3 className="font-semibold">{supportCategories.find(item => item.id === ticket.category)?.label}</h3><p className="text-sm text-muted-foreground mt-1 whitespace-pre-wrap break-words">{ticket.details}</p></div><div className="flex items-center gap-2"><SpeakButton label="حالة الطلب" text={`${supportCategories.find(item => item.id === ticket.category)?.label}. ${ticket.details}. الحالة: ${ticketStatusLabels[ticket.status]}.${ticket.status === 'resolved' && ticket.rating === null ? ' يمكنك تقييم الخدمة من واحد إلى خمسة.' : ''}`} /><span className="status-label" data-status={ticket.status === 'resolved' ? 'completed' : 'reviewing'} aria-live="polite">{ticketStatusLabels[ticket.status]}</span></div></div>
          <ol className="flex flex-wrap gap-2 mt-4 text-xs">{ticketSteps.map((step, i) => <li key={step} className={`rounded px-2 py-1 ${i <= current ? 'bg-secondary text-primary font-semibold' : 'bg-muted text-muted-foreground'}`}>{i < current || ticket.status === 'resolved' ? '✓ ' : ''}{ticketStatusLabels[step]}{ticket.history.find(item => item.status === step) ? ` · ${formatInterviewDate(ticket.history.find(item => item.status === step)!.date)}` : ''}</li>)}</ol>
          {ticket.status === 'resolved' && <div className="mt-4">{ticket.rating === null ? <div className="flex flex-wrap items-center gap-1" role="group" aria-label="قيّم الخدمة"><span className="text-sm me-2">قيّم الخدمة:</span>{[1, 2, 3, 4, 5].map(value => <Button key={value} size="icon" variant="ghost" aria-label={`${value.toLocaleString('ar-SA')} من ٥`} onClick={() => state.rateSupportTicket(ticket.id, value)}><Star /></Button>)}</div> : <p className="text-sm text-primary flex items-center gap-2"><Check className="size-4" />شكرًا لتقييمك: {ticket.rating.toLocaleString('ar-SA')} من ٥</p>}</div>}
        </article>;
      })}</div>}
    </section>
  </Workspace>;
}
