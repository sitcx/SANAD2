/** Client for the company endpoints of the Sanad API (src/agent/company_api.py). */
import type { ApplicationStatus } from './sanad-data';
import type { CommunicationMode } from './support-tickets';

// Public URL only (never a secret). Defaults to /api, which the web server forwards to the Python API.
export const API_URL: string = (import.meta.env['VITE_SANAD_API_URL'] as string | undefined) ?? '/api';
/** The signed-in demo candidate is stored in the API as this talent id. */
export const SELF_TALENT_ID = 'self';

export interface Posting { id: string; company: string; title: string; city: string | null; mode: string | null; salary: string | null; description: string | null; skills: string[]; min_years: number; applicants: number }
export interface Talent { id: string; name: string; mode: CommunicationMode; years: number; city: string | null; skills: string[] }
export interface RankedTalent { talent: Talent; status: ApplicationStatus; interview_at: string | null; match: number; suggested: boolean }
export interface Indicators {
  postings: number; applicants: number; average_match: number; interview_rate: number; hired: number; retention: number | null;
  by_mode: Record<CommunicationMode, { applicants: number; hired: number }>;
}

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } });
  } catch {
    throw new ApiError('تعذّر الاتصال بخادم سند. شغّل المشروع بالأمر python run.py ثم أعد المحاولة.', 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new ApiError(typeof body?.detail === 'string' ? body.detail : 'حدث خطأ في الخادم.', response.status);
  }
  return response.json() as Promise<T>;
}
const post = <T,>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) });

export const companyApi = {
  indicators: (jobId?: string) => request<Indicators>(`/company/indicators${jobId ? `?job_id=${encodeURIComponent(jobId)}` : ''}`),
  jobs: () => request<Posting[]>('/company/jobs'),
  createJob: (job: { title: string; skills: string[]; min_years: number }) => post<Posting>('/company/jobs', job),
  setMinYears: (jobId: string, minYears: number) => request<unknown>(`/company/jobs/${encodeURIComponent(jobId)}/min-years`, { method: 'PUT', body: JSON.stringify({ min_years: minYears }) }),
  candidates: (jobId: string, minYears: number, mustHave: string[]) => {
    const params = new URLSearchParams({ min_years: String(minYears) });
    mustHave.forEach(skill => params.append('must_have', skill));
    return request<RankedTalent[]>(`/company/jobs/${encodeURIComponent(jobId)}/candidates?${params}`);
  },
  setStatus: (jobId: string, talentId: string, status: ApplicationStatus) => post<unknown>(`/company/jobs/${encodeURIComponent(jobId)}/candidates/${encodeURIComponent(talentId)}/status`, { status }),
  schedule: (jobId: string, talentId: string, interviewAt: string) => post<{ interview_at: string }>(`/company/jobs/${encodeURIComponent(jobId)}/candidates/${encodeURIComponent(talentId)}/schedule`, { interview_at: interviewAt }),
  reset: () => post<unknown>('/company/reset', {}),
};

export const candidateApi = {
  applications: () => request<{ posting_id: string; status: ApplicationStatus; interview_at: string | null }[]>(`/candidate/${SELF_TALENT_ID}/applications`),
  setStatus: (jobId: string, status: ApplicationStatus) => post<unknown>(`/candidate/${SELF_TALENT_ID}/applications/${encodeURIComponent(jobId)}`, { status }),
};
