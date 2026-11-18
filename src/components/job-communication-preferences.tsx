import { Check, Ear, Hand, MessageSquareText, PencilLine, ScanFace } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { useSanad } from '@/lib/sanad-context';
import { communicationPreferences } from '@/lib/sanad-data';
import { cn } from '@/lib/utils';

const preferenceIcons = {
  sign: Hand,
  text: MessageSquareText,
  'lip-reading': ScanFace,
  'hearing-aid': Ear,
  other: PencilLine,
};

export function JobCommunicationPreferences({ jobId }: { jobId: string }) {
  const state = useSanad();
  const selected = state.preferences[jobId] ?? [];
  const otherNeeds = state.additionalCommunicationNeeds[jobId] ?? '';

  return <div className="border-t border-border mt-6 pt-5">
    <fieldset aria-describedby={`communication-description-${jobId}`}>
      <legend className="font-semibold text-lg">كيف تفضّل أن نتواصل معك أثناء المقابلة؟</legend>
      <p id={`communication-description-${jobId}`} className="text-sm text-muted-foreground mt-2 mb-5 leading-loose">اختر طرق التواصل التي تناسبك لتجهيز مقابلة مريحة ومناسبة لاحتياجاتك.</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {communicationPreferences.map(item => {
          const Icon = preferenceIcons[item.id];
          const checked = selected.includes(item.id);
          const id = `communication-${jobId}-${item.id}`;
          return <label key={item.id} htmlFor={id} className={cn(
            'grid grid-cols-[2.25rem_minmax(0,1fr)_1.25rem] items-start gap-3 rounded-lg border p-4 min-h-32 cursor-pointer transition-colors focus-within:outline-2 focus-within:outline-ring focus-within:outline-offset-2',
            checked ? 'border-primary bg-secondary' : 'border-border bg-card hover:border-primary',
          )}>
            <span aria-hidden="true" className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted text-primary"><Icon className="size-6" /></span>
            <span className="min-w-0">
              <span id={`${id}-label`} className="block text-sm font-semibold leading-7">{item.label}</span>
              <span id={`${id}-description`} className="block text-sm text-muted-foreground leading-loose mt-1">{item.description}</span>
            </span>
            <Checkbox id={id} className="size-5 mt-1 shadow-none" checked={checked} aria-labelledby={`${id}-label`} aria-describedby={`${id}-description`} onCheckedChange={value => state.setJobPreferences(jobId, value === true ? [...selected, item.id] : selected.filter(value => value !== item.id))} />
          </label>;
        })}
      </div>
      {selected.includes('other') && <div className="mt-5">
        <label htmlFor={`communication-other-details-${jobId}`} className="block text-sm font-semibold mb-2">ما احتياجك الإضافي؟</label>
        <Textarea id={`communication-other-details-${jobId}`} value={otherNeeds} onChange={event => state.setAdditionalCommunicationNeeds(jobId, event.target.value)} rows={3} className="min-h-28 bg-card resize-y" />
      </div>}
    </fieldset>
    <p className="text-xs text-muted-foreground leading-loose mt-4">تُحفظ تفضيلاتك في ملفك لهذه الوظيفة خلال الجلسة فقط، وتظهر في عرض الشركة التجريبي. لا تعني اختياراتك توفير مترجم أو تحويل الكلام تلقائيًا؛ هذه الخدمات غير متصلة حاليًا.</p>
    <Button variant="outline" className="mt-5 max-w-full whitespace-normal h-auto min-h-11" disabled={state.reviewedPlans.includes(jobId)} onClick={() => state.reviewPlan(jobId)}><Check />{state.reviewedPlans.includes(jobId) ? 'تمت مراجعة خطة التهيئة' : 'تأكيد مراجعة خطة التهيئة'}</Button>
  </div>;
}