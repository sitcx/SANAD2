/** Client for the job-agent endpoints of the Sanad API (src/agent/candidate_api.py): CV reading, matching and job search. */
import { API_URL, ApiError, SELF_TALENT_ID } from './company-api';

export interface AtsCheck { id: string; label: string; weight: number; score: number; tip: string }
export interface CvProfile {
  summary: string; skills: string[]; experience: string[]; education: string[]; jobTitles: string[]; languages: string[];
  suggestedRoles: string[]; careerLevel: string; yearsExperience: number; engine: string;
  ats?: { score: number; rating: string; checks: AtsCheck[]; tips: string[] };
}
export interface AgentPosting { id: string; title: string; company: string | null; city: string | null; mode: string | null; salary: string | null; source: string; source_name: string | null; source_url: string | null }
export interface AgentMatch { job_id: string; match: number; reason: string; matched_skills: string[]; missing_skills: string[]; job: AgentPosting }
export interface AgentProfile { profile: CvProfile | null; matches: AgentMatch[]; webSearchEnabled: boolean }
export interface UploadResult { status: 'ok' | 'need_info' | 'failed'; error?: string; missing_info?: ('skills' | 'city')[] }

const NETWORK_ERROR = 'تعذّر الاتصال بخادم سند. شغّل المشروع بالأمر python run.py ثم أعد المحاولة.';

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(NETWORK_ERROR, 0);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new ApiError(typeof body?.detail === 'string' ? body.detail : 'حدث خطأ في الخادم.', response.status);
  }
  return response.json() as Promise<T>;
}

export const cvApi = {
  /** Reads the CV like an ATS (and with Claude when a key is set), matches every job, then searches for new ones in the background. */
  upload: (file: File, answers?: { city?: string }) => {
    const form = new FormData();
    form.append('cv', file);
    if (answers) form.append('answers', JSON.stringify(answers));
    return call<UploadResult>(`/candidate/${SELF_TALENT_ID}/cv`, { method: 'POST', body: form });
  },
  /** The stored reading of the CV and the matched jobs, best first. */
  profile: () => call<AgentProfile>(`/candidate/${SELF_TALENT_ID}/profile`),
};

/** Cities the agent understands (Arabic label → value sent to the API). */
export const agentCities = ['الرياض', 'جدة', 'الدمام', 'الخبر', 'مكة', 'المدينة', 'أبها', 'تبوك', 'عن بعد'];
