import { createFileRoute } from '@tanstack/react-router';
import { Search, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { JobCard } from '@/components/job-card';
import { jobs, matchesRegion } from '@/lib/sanad-data';
import { useSanad } from '@/lib/sanad-context';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/jobs')({ head: () => pageHead('الوظائف', 'الوظائف المتاحة والمناسبة لسيرتك، وطلباتك وترشيحات المقابلات مع تفاصيل التهيئة.'), component: Jobs });
function Jobs() {
  const state = useSanad();
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [view, setView] = useState('all');
  const [region, setRegion] = useState('all');
  const filtered = jobs.filter(job => `${job.title} ${job.english} ${job.company} ${job.skills.join(' ')}`.toLowerCase().includes(search.toLowerCase()) && (filter === 'all' || job.mode === filter) && matchesRegion(job, region) && (view === 'all' || (view === 'matching' && state.cvStatus === 'analysed')));
  return <Workspace><PageTitle title="الوظائف" subtitle="اكتشف فرص العمل التي تناسب مهاراتك وموقعك." /><Tabs value={view} onValueChange={setView} dir="rtl"><TabsList className="mb-5 h-auto flex w-fit max-w-full flex-wrap gap-1"><TabsTrigger className="min-h-11" value="all">كل الوظائف</TabsTrigger><TabsTrigger className="min-h-11" value="matching">الوظائف المناسبة لك</TabsTrigger></TabsList><TabsContent value={view}>
    <div className="relative mb-4"><Search className="absolute right-4 top-3.5 size-5 text-muted-foreground" /><Input value={search} onChange={e => setSearch(e.target.value)} aria-label="البحث في الوظائف" placeholder="ابحث عن وظيفة، شركة أو مهارة..." className="h-12 pr-12 bg-card" /></div><div className="flex flex-wrap items-center justify-between gap-3 mb-6"><Select value={region} onValueChange={setRegion} dir="rtl"><SelectTrigger className="w-56" aria-label="المنطقة الجغرافية"><SelectValue /></SelectTrigger><SelectContent>{[{ value: 'all', label: 'كل المناطق' }, { value: 'الرياض', label: 'منطقة الرياض' }, { value: 'جدة', label: 'منطقة مكة المكرمة · جدة' }, { value: 'الدمام', label: 'المنطقة الشرقية' }, { value: 'المدينة', label: 'منطقة المدينة المنورة' }, { value: 'remote', label: 'عن بُعد · جميع المناطق' }].map(item => <SelectItem key={item.value} value={item.value}>{item.label}</SelectItem>)}</SelectContent></Select><div className="flex gap-2" role="group" aria-label="نوع العمل">{[{ value: 'all', label: 'كل الأنواع' }, { value: 'عن بُعد', label: 'عن بُعد' }, { value: 'هجين', label: 'هجين' }].map(item => <Button key={item.value} variant={filter === item.value ? 'secondary' : 'ghost'} size="sm" aria-pressed={filter === item.value} onClick={() => setFilter(item.value)}>{item.label}</Button>)}</div><p role="status" className="text-xs text-muted-foreground">{filtered.length.toLocaleString('ar-SA')} فرص</p></div>
    <div className="space-y-4">{filtered.map(job => <JobCard key={job.id} job={job} />)}</div>
    {filtered.length === 0 && <div className="py-12 text-center"><Search className="size-8 mx-auto text-muted-foreground mb-3" /><h2 className="font-semibold">{view === 'matching' && state.cvStatus !== 'analysed' ? 'أكمل تحليل سيرتك في لوحة التحكم' : 'لا توجد فرص مطابقة'}</h2><Button variant="outline" className="mt-4" onClick={() => { setSearch(''); setFilter('all'); setRegion('all'); setView('all'); }}>عرض جميع الوظائف</Button></div>}
    <p className="flex items-start gap-2 text-xs text-muted-foreground mt-6"><ShieldCheck className="size-5 text-primary shrink-0" />التوافق توصية تجريبية، وليس قرار قبول أو استبعاد.</p>
  </TabsContent></Tabs></Workspace>;
}
