/** Post-hire support: the employee raises a request and the Sanad team follows it until resolved. */
export type CommunicationMode = 'sign' | 'voice';
export type TicketStatus = 'received' | 'in_progress' | 'resolved';

export const ticketStatusLabels: Record<TicketStatus, string> = {
  received: 'تم الاستلام',
  in_progress: 'قيد المعالجة',
  resolved: 'تم الحل',
};
export const ticketSteps: TicketStatus[] = ['received', 'in_progress', 'resolved'];

export const supportCategories = [
  { id: 'interpreter', audience: 'sign', label: 'مترجم إشارة لاجتماع أو تدريب' },
  { id: 'captions', audience: 'sign', label: 'ترجمة نصية لاجتماع' },
  { id: 'accessible-document', audience: 'voice', label: 'تهيئة مستند أو نظام ليُقرأ بالصوت' },
  { id: 'screen-reader', audience: 'voice', label: 'مساعدة في برنامج قارئ الشاشة' },
  { id: 'general', audience: 'all', label: 'صعوبة أخرى في التواصل أو بيئة العمل' },
] as const;
export type SupportCategory = (typeof supportCategories)[number]['id'];

export function categoriesFor(mode: CommunicationMode) {
  return supportCategories.filter(item => item.audience === mode || item.audience === 'all');
}

export interface SupportTicket {
  id: string;
  jobId: string;
  category: SupportCategory;
  details: string;
  status: TicketStatus;
  history: { status: TicketStatus; date: string }[];
  rating: number | null;
}

export function createTicket(id: string, jobId: string, category: SupportCategory, details: string, date: string): SupportTicket | null {
  if (!supportCategories.some(item => item.id === category) || !details.trim()) return null;
  return { id, jobId, category, details: details.trim(), status: 'received', history: [{ status: 'received', date }], rating: null };
}

export function advanceTicket(ticket: SupportTicket, date: string): SupportTicket {
  const next = ticketSteps[ticketSteps.indexOf(ticket.status) + 1];
  return next ? { ...ticket, status: next, history: [...ticket.history, { status: next, date }] } : ticket;
}

/** Rating is allowed once, only after the request is resolved. */
export function rateTicket(ticket: SupportTicket, rating: number): SupportTicket {
  if (ticket.status !== 'resolved' || ticket.rating !== null || !Number.isInteger(rating) || rating < 1 || rating > 5) return ticket;
  return { ...ticket, rating };
}
