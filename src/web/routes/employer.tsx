import { createFileRoute, Navigate } from '@tanstack/react-router';
import { pageHead } from '@/lib/page-head';

export const Route = createFileRoute('/employer')({
  head: () => pageHead('فرص الشركات', 'الوظائف وخطط التهيئة متاحة ضمن تجربة الوظائف الموحدة في سَند.'),
  component: Employer,
});
function Employer() {
  return <Navigate to="/jobs" replace />;
}
