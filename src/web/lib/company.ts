import { mockCvProfile, type ApplicationStatus } from './sanad-data';
import type { CommunicationMode } from './support-tickets';

/** Company side: jobs with requirements, a candidate pool, filtering and indicators. */
export interface CompanyJob { id: string; title: string; skills: string[]; minYears: number; custom?: boolean }
export interface PoolCandidate {
  id: string;
  name: string;
  mode: CommunicationMode;
  years: number;
  skills: string[];
  applications: Record<string, ApplicationStatus>;
  /** For hired candidates: still in the job after hiring. */
  retained?: boolean;
}

export const SELF_ID = 'self';
export const yearOptions = [
  { value: 0, label: 'كل سنوات الخبرة' },
  { value: 1, label: 'سنة فأكثر' },
  { value: 2, label: 'سنتان فأكثر' },
  { value: 3, label: 'ثلاث سنوات فأكثر' },
] as const;

export const candidatePool: PoolCandidate[] = [
  { id: 'c1', name: 'نورة', mode: 'sign', years: 3, skills: ['Excel', 'SQL', 'تحليل البيانات', 'Power BI'], applications: { analyst: 'reviewing' } },
  { id: 'c2', name: 'فهد', mode: 'voice', years: 1, skills: ['Excel', 'التواصل الكتابي', 'CRM'], applications: { support: 'applied', analyst: 'applied' } },
  { id: 'c3', name: 'ريم', mode: 'sign', years: 2, skills: ['Figma', 'التصميم', 'بحث المستخدم'], applications: { designer: 'nominated' } },
  { id: 'c4', name: 'عبدالله', mode: 'voice', years: 4, skills: ['SQL', 'Python', 'تحليل البيانات'], applications: { analyst: 'hired' }, retained: true },
  { id: 'c5', name: 'هيا', mode: 'sign', years: 1, skills: ['التواصل الكتابي', 'حل المشكلات', 'CRM'], applications: { support: 'completed' } },
  { id: 'c6', name: 'سلمان', mode: 'voice', years: 2, skills: ['Figma', 'التصميم'], applications: { designer: 'applied' } },
  { id: 'c7', name: 'لمى', mode: 'sign', years: 5, skills: ['CRM', 'حل المشكلات', 'التواصل الكتابي'], applications: { support: 'hired' }, retained: true },
  { id: 'c8', name: 'ماجد', mode: 'sign', years: 3, skills: ['Excel', 'تحليل البيانات'], applications: { analyst: 'hired' }, retained: false },
];

/** The signed-in candidate as the company sees them (skills from the analysed CV). */
export function selfCandidate(name: string, mode: CommunicationMode, applications: Record<string, ApplicationStatus>): PoolCandidate {
  return { id: SELF_ID, name, mode, years: 2, skills: [...mockCvProfile.skills], applications: { ...applications }, retained: true };
}

/** Share of the job's required skills the candidate has (0–100). */
export function matchScore(candidate: Pick<PoolCandidate, 'skills'>, required: readonly string[]): number {
  if (!required.length) return 0;
  const owned = new Set(candidate.skills.map(skill => skill.toLowerCase()));
  return Math.round(required.filter(skill => owned.has(skill.toLowerCase())).length / required.length * 100);
}

export interface CandidateFilter { minYears: number; mustHave: readonly string[] }
export interface RankedCandidate { candidate: PoolCandidate; status: ApplicationStatus; match: number }

/**
 * Applicants for a job, filtered by what the company needs and ranked by match.
 * A new job has no applicants yet, so Sanad suggests matching candidates from the pool.
 */
export function rankCandidates(job: CompanyJob, pool: readonly PoolCandidate[], filter: CandidateFilter): RankedCandidate[] {
  const applicants = pool.filter(candidate => (candidate.applications[job.id] ?? 'available') !== 'available');
  const base = applicants.length || !job.custom ? applicants : pool.filter(candidate => matchScore(candidate, job.skills) > 0);
  const mustHave = filter.mustHave.map(skill => skill.toLowerCase());
  return base
    .filter(candidate => candidate.years >= filter.minYears)
    .filter(candidate => mustHave.every(skill => candidate.skills.some(owned => owned.toLowerCase() === skill)))
    .map(candidate => ({ candidate, status: candidate.applications[job.id] ?? 'available', match: matchScore(candidate, job.skills) }))
    .sort((a, b) => b.match - a.match || b.candidate.years - a.candidate.years);
}

const reachedInterview: ApplicationStatus[] = ['nominated', 'scheduled', 'completed', 'accepted', 'hired'];

export interface CompanyIndicators { applicants: number; averageMatch: number; interviewRate: number; hired: number; retention: number | null }

export function companyIndicators(jobs: readonly CompanyJob[], pool: readonly PoolCandidate[]): CompanyIndicators {
  const entries = jobs.flatMap(job => pool
    .filter(candidate => (candidate.applications[job.id] ?? 'available') !== 'available')
    .map(candidate => ({ candidate, status: candidate.applications[job.id]!, match: matchScore(candidate, job.skills) })));
  const hired = entries.filter(entry => entry.status === 'hired');
  const percent = (part: number, whole: number) => whole ? Math.round(part / whole * 100) : 0;
  return {
    applicants: entries.length,
    averageMatch: entries.length ? Math.round(entries.reduce((sum, entry) => sum + entry.match, 0) / entries.length) : 0,
    interviewRate: percent(entries.filter(entry => reachedInterview.includes(entry.status)).length, entries.length),
    hired: hired.length,
    retention: hired.length ? percent(hired.filter(entry => entry.candidate.retained !== false).length, hired.length) : null,
  };
}

/** What the company can do next with a candidate in each status. */
export function companyActions(status: ApplicationStatus): ('nominate' | 'schedule' | 'complete' | 'accept' | 'reject')[] {
  switch (status) {
    case 'applied': case 'reviewing': return ['nominate', 'reject'];
    case 'nominated': return ['schedule', 'reject'];
    case 'scheduled': return ['complete'];
    case 'completed': return ['accept', 'reject'];
    default: return [];
  }
}
