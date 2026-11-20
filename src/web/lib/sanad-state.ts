import { createContext, type Context } from 'react';
import type { ApplicationStatus, CvStatus, InterviewReport } from './sanad-data';
import type { TrainingProgress } from './training-readiness';

export interface SanadState {
  candidateName: string;
  candidateEmail: string;
  signedIn: boolean;
  signIn: (name: string, email?: string) => void;
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
  practiceCompleted: boolean;
  trainingProgress: TrainingProgress;
  completeTrainingQuestion: (jobId: string, questionIndex: number) => void;
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