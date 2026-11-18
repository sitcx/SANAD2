import { createFileRoute, Link } from '@tanstack/react-router';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PageTitle, Workspace } from '@/components/sanad-layout';
import { ApplicationTracker } from '@/components/application-tracker';
import { pageHead } from '@/lib/page-head';
export const Route = createFileRoute('/applications')({ head: () => pageHead('تتبع تقديماتي', 'مراحل طلبات التوظيف في خط زمني بصري واضح، مع الحالة الحالية والتواريخ والخطوة التالية.'), component: Applications });
function Applications() {
  return <Workspace><Button asChild variant="ghost" className="mb-2 px-2"><Link to="/dashboard" aria-label="العودة إلى لوحة التحكم"><ArrowRight />العودة إلى لوحة التحكم</Link></Button><PageTitle title="تتبع تقديماتي" subtitle="جميع طلباتك، حالاتها، وخطوتك التالية." /><ApplicationTracker /></Workspace>;
}
