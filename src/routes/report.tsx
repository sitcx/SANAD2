import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowLeft, Check, Clock3, Download, FileCheck2, Lightbulb, LoaderCircle, Share2, ShieldCheck, Target } from 'lucide-react';
import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { useSanad } from '@/lib/sanad-context';
import { formatInterviewDate, jobs, liveQuestionSets } from '@/lib/sanad-data';
import { downloadReportPdf } from '@/lib/report-pdf';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/report')({ head: () => pageHead('تقارير المقابلات', 'ملخص المقابلة والمهارات والأسئلة والإجابات المعتمدة، مع تحميل PDF ومشاركة تجريبية مع الشركة.'), component: Report });
function Report() {
  const state = useSanad(); const [reportId, setReportId] = useState<string>();
  const report = state.reports.find(item => item.id === reportId) ?? state.reports[0];
  const job = jobs.find(item => item.id === report?.jobId) ?? jobs[0];
  const documentRef = useRef<HTMLDivElement>(null);
  const [downloading, setDownloading] = useState(false); const [downloaded, setDownloaded] = useState(false); const [error, setError] = useState('');
  const [sharing, setSharing] = useState(false); const [sharedReportIds, setSharedReportIds] = useState<string[]>([]);
  const answers = report?.answers ?? []; const sample = report?.id === 'previous-analyst';
  const shared = report ? sharedReportIds.includes(report.id) : false;
  const duration = report?.durationSeconds ?? 1800;
  async function download() {
    if (!documentRef.current) return; setDownloading(true); setError('');
    try { await downloadReportPdf(documentRef.current); setDownloaded(true); } catch { setError('تعذّر تحميل التقرير. حاول مرة أخرى.'); } finally { setDownloading(false); }
  }
  return <Workspace><PageTitle title="التقارير" subtitle="مقابلاتك السابقة وإجاباتك التي اعتمدتها." />
    <div className="mb-6"><label className="block text-sm font-medium mb-2" htmlFor="report-selection">اختر تقرير المقابلة</label><Select value={report?.id ?? ''} onValueChange={id => { setReportId(id); setDownloaded(false); setError(''); }} dir="rtl"><SelectTrigger id="report-selection" className="bg-card h-auto min-h-12 [&>span]:line-clamp-none [&>span]:whitespace-normal [&>span]:text-start"><SelectValue /></SelectTrigger><SelectContent>{state.reports.map(item => { const reportJob = jobs.find(job => job.id === item.jobId); return <SelectItem value={item.id} key={item.id}>{reportJob?.title} · {formatInterviewDate(item.date)}</SelectItem>; })}</SelectContent></Select></div>
    <div ref={documentRef} className="report-content" dir="rtl"><p className="eyebrow">سَند · {sample ? 'تقرير افتراضي سابق' : 'ملخص الجلسة التجريبية'}</p><h2 className="page-heading mt-2">تقرير مقابلة {state.candidateName}</h2><p className="text-sm text-muted-foreground mt-2">بيانات تجريبية وليست تقييمًا فعليًا أو قرار توظيف.</p>
      <dl className="report-summary mt-6 text-sm"><div><dt className="text-muted-foreground">الوظيفة</dt><dd className="font-semibold mt-1">{job.title}</dd></div><div><dt className="text-muted-foreground">الشركة</dt><dd className="font-semibold mt-1">{job.company}</dd></div><div><dt className="text-muted-foreground">تاريخ المقابلة · بتوقيت الرياض</dt><dd className="mt-1">{report ? formatInterviewDate(report.date) : 'لا يوجد تقرير'}</dd></div><div><dt className="text-muted-foreground">مدة المقابلة</dt><dd className="flex items-center gap-2 mt-1"><Clock3 className="size-4 text-primary" />{Math.floor(duration / 60).toLocaleString('ar-SA')} دقيقة و{(duration % 60).toLocaleString('ar-SA')} ثانية</dd></div></dl>
      <section className="workspace-section"><h3 className="font-semibold text-lg">ملخص المقابلة</h3><p className="text-sm text-muted-foreground mt-3 leading-loose">{answers.length ? `ناقشت المقابلة الخبرات المرتبطة بوظيفة ${job.title}. اعتمد المرشح ${answers.length.toLocaleString('ar-SA')} إجابات. لا يتضمن الملخص أي مسودة أو تقييم لطريقة التواصل.` : 'انتهت المقابلة دون إجابات معتمدة؛ لم تدخل أي مسودة في التقرير.'}</p></section>
      <div className="grid gap-x-7 sm:grid-cols-2"><section className="workspace-section"><h3 className="font-semibold flex items-center gap-2"><Check className="size-5 text-primary" />نقاط القوة · أمثلة تجريبية</h3><ul className="text-sm text-muted-foreground mt-4 space-y-3"><li>ربط الخبرة بمواقف عملية.</li><li>شرح خطوات حل المشكلة.</li><li>استخدام مهارات مرتبطة بالدور.</li></ul></section><section className="workspace-section"><h3 className="font-semibold flex items-center gap-2"><Target className="size-5 text-primary" />المهارات التي تم تقييمها</h3><div className="flex flex-wrap gap-2 mt-4">{(state.jobSkills[job.id] ?? job.skills).map(skill => <span key={skill} className="skill-tag">{skill}</span>)}</div><p className="text-xs text-muted-foreground mt-3">هذه مهارات الدور في النموذج، وليست نتيجة تحليل آلي لإجاباتك.</p></section></div>
      <section className="workspace-section"><h3 className="font-semibold text-lg mb-5">الأسئلة والإجابات المعتمدة</h3>{answers.length ? <ol className="space-y-6">{answers.map((answer, index) => <li key={`${index}-${answer}`} className="border-b border-border pb-5"><p className="text-xs text-primary flex gap-2 items-center"><ShieldCheck className="size-4" />إجابة {(index + 1).toLocaleString('ar-SA')} · اعتمدها المرشح</p><h4 className="font-semibold text-sm mt-3">{report?.questions?.[index] || liveQuestionSets[job.id][index]?.original || 'سؤال المقابلة'}</h4><p className="text-sm leading-loose mt-2">{answer}</p></li>)}</ol> : <p className="text-sm text-muted-foreground flex gap-2"><FileCheck2 className="size-5" />لا توجد إجابات معتمدة.</p>}</section>
      <section className="workspace-section"><h3 className="font-semibold flex gap-2 items-center"><Lightbulb className="size-5 text-primary" />ملاحظات التطوير</h3><p className="text-sm text-muted-foreground mt-3 leading-loose">أضف نتيجة محددة لكل مثال في المقابلة القادمة. رتّب إجابتك إلى: المشكلة، ما فعلته، والنتيجة.</p></section>
      <p className="bg-secondary text-secondary-foreground p-4 rounded-md text-sm flex items-start gap-3"><ShieldCheck className="size-6 shrink-0" /><span>هذا التقرير يلخص أداء المرشح ومهاراته، ولا يقيس قدرته بناءً على طريقة التواصل.</span></p>
    </div>
    <div className="flex flex-wrap gap-3 justify-end mt-6"><Button variant="outline" onClick={download} disabled={downloading || !report}>{downloading ? <LoaderCircle className="animate-spin" /> : <Download />}{downloading ? 'جارٍ تجهيز التقرير…' : 'تحميل التقرير PDF'}</Button><Button disabled={!report || shared} onClick={() => setSharing(true)}><Share2 />{shared ? 'تمت المشاركة تجريبيًا' : 'مشاركة التقرير مع الشركة'}</Button><Button asChild variant="ghost"><Link to="/coach">متابعة التدريب<ArrowLeft /></Link></Button></div><p role="status" className="text-sm text-primary mt-3">{downloaded ? 'تم تحميل التقرير بصيغة PDF.' : shared ? 'تمت محاكاة مشاركة التقرير؛ لم يُرسل إلى شركة حقيقية.' : ''}</p>{error && <p role="alert" className="text-sm text-destructive mt-3">{error}</p>}
    <Dialog open={sharing} onOpenChange={setSharing}><DialogContent dir="rtl"><DialogTitle>مشاركة التقرير مع {job.company}؟</DialogTitle><DialogDescription>يحتوي التقرير على إجاباتك المعتمدة فقط. هذه مشاركة تجريبية؛ لا يتم إرسال بيانات إلى شركة حقيقية.</DialogDescription><div className="flex gap-3"><Button variant="outline" onClick={() => setSharing(false)}>إلغاء</Button><Button onClick={() => { if (report) setSharedReportIds(current => [...current, report.id]); setSharing(false); }}><Share2 />تأكيد المشاركة التجريبية</Button></div></DialogContent></Dialog>
  </Workspace>;
}