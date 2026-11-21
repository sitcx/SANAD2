import { createContext, type Context } from 'react';
import type { ApplicationStatus, CvStatus, InterviewReport } from './sanad-data';
import type { CareerTrackId } from './career-discovery';
import type { CompanyJob } from './company';
import type { CommunicationMode, SupportCategory, SupportTicket } from './support-tickets';

export type AccountRole = 'candidate' | 'company';

export interface SanadState {
  candidateName: string;
  candidateEmail: string;
  signedIn: boolean;
  signIn: (name: string, email?: string, mode?: CommunicationMode, role?: AccountRole) => void;
  role: AccountRole;
  /** Demo only: switch between the two accounts while keeping the shared session data. */
  switchRole: (role: AccountRole) => void;
  companyName: string;
  companyJobs: CompanyJob[];
  addCompanyJob: (title: string, skills: string[], minYears: number) => string | null;
  jobMinYears: Record<string, number>;
  setJobMinYears: (id: string, years: number) => void;
  poolApplications: Record<string, Record<string, ApplicationStatus>>;
  poolSchedules: Record<string, string>;
  companyUpdateCandidate: (candidateId: string, jobId: string, status: ApplicationStatus) => void;
  companySchedule: (candidateId: string, jobId: string, date: string) => string | null;
  /** Mirror a status already saved by the API for the signed-in candidate. */
  syncSelfApplication: (jobId: string, status: ApplicationStatus, interviewAt?: string | null) => void;
  communicationMode: CommunicationMode;
  setCommunicationMode: (mode: CommunicationMode) => void;
  careerTrack: CareerTrackId | null;
  careerDecided: boolean;
  completeCareerDiscovery: (track: CareerTrackId) => void;
  skipCareerDiscovery: () => void;
  acceptOffer: (id: string) => void;
  supportTickets: SupportTicket[];
  submitSupportTicket: (category: SupportCategory, details: string) => boolean;
  rateSupportTicket: (id: string, rating: number) => void;
  updateProfile: (name: string, email: string) => void;
  signOut: () => void;
  guideOpen: boolean;
  openGuide: () => void;
  closeGuide: () => void;
  schedules: Record<string, string>;
  scheduleInterview: (id: string, date: string) => string | null;
  termsAccepted: boolean;
  setTermsAccepted: (value: boolean) => void;
  trainingConsent: boolean;
  setTrainingConsent: (value: boolean) => void;
  darkMode: boolean;
  largeText: boolean;
  setLargeText: (value: boolean) => void;
  setDarkMode: (value: boolean) => void;
  applicationDates: Record<string, string>;
  applicationHistory: Record<string, { status: ApplicationStatus; date: string }[]>;
  updateApplication: (id: string, status: ApplicationStatus) => void;
  jobSkills: Record<string, string[]>;
  setJobSkills: (id: string, skills: string[]) => void;
  selectedJobId: string;
  selectJob: (id: string) => void;
  cvName: string;
  setCvName: (name: string) => void;
  cvStatus: CvStatus;
  setCvStatus: (status: CvStatus) => void;
  applications: Record<string, ApplicationStatus>;
  applyToJob: (id: string) => void;
  nominateJob: (id: string) => void;
  reviewedPlans: string[];
  reviewPlan: (id: string) => void;
  preferences: Record<string, string[]>;
  setJobPreferences: (id: string, preferences: string[]) => void;
  additionalCommunicationNeeds: Record<string, string>;
  setAdditionalCommunicationNeeds: (id: string, value: string) => void;
  now: number | undefined;
  reports: InterviewReport[];
  finishInterview: (questions?: string[], durationSeconds?: number) => void;
  interpreterRequested: boolean;
  setInterpreterRequested: (requested: boolean) => void;
  interviewCompleted: boolean;
  setInterviewCompleted: (completed: boolean) => void;
  sentAnswers: string[];
  setSentAnswers: (answers: string[]) => void;
}

// Keep the context identity separate from Fast Refresh component exports.
// Only the context object survives development updates; candidate data remains
// inside each mounted provider, never in a shared module-level store.
export const SanadContext: Context<SanadState | null> = import.meta.hot?.data?.sanadContext ?? createContext<SanadState | null>(null);
SanadContext.displayName = 'SanadContext';
if (import.meta.hot?.data) {
  // Preview may evaluate different query URLs before any module is disposed.
  // Save the identity now so every evaluation uses the same provider connection.
  import.meta.hot.data.sanadContext = SanadContext;
}