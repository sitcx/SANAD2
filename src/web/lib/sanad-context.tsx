import { useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { canUpdateApplication, communicationPreferences, scheduleConflict, interviewSchedules, jobs, previousReports, type ApplicationStatus, type CvStatus, type InterviewReport } from './sanad-data';
import { SanadContext } from './sanad-state';
import { getTrainingReadiness, recordTrainingQuestion, type TrainingProgress } from './training-readiness';
export function SanadProvider({ children }: { children: ReactNode }) {
  const [sessionKey, setSessionKey] = useState(0);
  const signOut = useCallback(() => setSessionKey(current => current + 1), []);
  return <SanadSessionProvider key={sessionKey} signOut={signOut}>{children}</SanadSessionProvider>;
}

function SanadSessionProvider({ children, signOut }: { children: ReactNode; signOut: () => void }) {
  const [candidateName, setCandidateName] = useState('أحمد');
  const [candidateEmail, setCandidateEmail] = useState('');
  const [signedIn, setSignedIn] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [trainingConsent, setTrainingConsent] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [schedules, setSchedules] = useState<Record<string, string>>(interviewSchedules);
  const [applicationDates, setApplicationDates] = useState<Record<string, string>>({ analyst: '2026-11-12T09:00:00+03:00', support: '2026-11-13T09:00:00+03:00' });
  const [applicationHistory, setApplicationHistory] = useState<Record<string, { status: ApplicationStatus; date: string }[]>>({
    analyst: [{ status: 'applied', date: '2026-11-12T09:00:00+03:00' }, { status: 'reviewing', date: '2026-11-13T09:00:00+03:00' }, { status: 'nominated', date: '2026-11-14T09:00:00+03:00' }],
    support: [{ status: 'applied', date: '2026-11-13T09:00:00+03:00' }, { status: 'reviewing', date: '2026-11-14T09:00:00+03:00' }, { status: 'nominated', date: '2026-11-15T09:00:00+03:00' }],
  });
  const [jobSkills, setSkills] = useState<Record<string, string[]>>({});
  const [selectedJobId, setSelectedJobId] = useState<string>(jobs[0].id);
  const [cvName, setCvName] = useState('أحمد_السيرة_الذاتية.pdf');
  const [cvStatus, setCvStatus] = useState<CvStatus>('analysed');
  const [applications, setApplications] = useState<Record<string, ApplicationStatus>>({ analyst: 'nominated', support: 'nominated', designer: 'available' });
  const [reviewedPlans, setReviewedPlans] = useState<string[]>([]);
  const [preferences, setPreferences] = useState<Record<string, string[]>>({});
  const [additionalCommunicationNeeds, setAdditionalNeeds] = useState<Record<string, string>>({});
  const [now, setNow] = useState<number>();
  const [reports, setReports] = useState<InterviewReport[]>(previousReports);
  const [interpreterRequested, setInterpreterRequested] = useState(false);
  const [trainingProgress, setTrainingProgress] = useState<TrainingProgress>({});
  const practiceCompleted = getTrainingReadiness(trainingProgress[selectedJobId]) === 100;
  const [interviewCompleted, setInterviewCompleted] = useState(false);
  const [sentAnswers, setSentAnswers] = useState<string[]>([]);
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    return () => document.documentElement.classList.remove('dark');
  }, [darkMode]);
  useEffect(() => {
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  function signIn(name: string, email = '') { if (!name.trim()) return; setCandidateName(name.trim()); setCandidateEmail(email.trim()); setSignedIn(true); }
  function updateProfile(name: string, email: string) {
    if (!signedIn || !name.trim() || !/^\S+@\S+\.\S+$/.test(email.trim())) return;
    setCandidateName(name.trim()); setCandidateEmail(email.trim());
  }
  function updateApplication(id: string, status: ApplicationStatus) {
    if (!jobs.some(job => job.id === id) || !canUpdateApplication(applications[id] ?? 'available', status)) return;
    const date = new Date().toISOString();
    setApplications(current => ({ ...current, [id]: status }));
    setApplicationHistory(current => ({ ...current, [id]: [...(current[id] ?? []), { status, date }] }));
    if (status === 'applied') setApplicationDates(current => ({ ...current, [id]: date }));
  }
  function scheduleInterview(id: string, date: string) {
    if (!jobs.some(job => job.id === id)) return 'الوظيفة غير موجودة.';
    const conflict = scheduleConflict(id, date, schedules);
    if (conflict) return conflict;
    setSchedules(current => ({ ...current, [id]: date }));
    const timestamp = new Date().toISOString();
    setApplicationHistory(current => ({ ...current, [id]: [...(current[id] ?? []), { status: applications[id] ?? 'available', date: timestamp }] }));
    return null;
  }
  useEffect(() => {
    if (cvStatus !== 'analysing') return;
    const timer = window.setTimeout(() => setCvStatus('analysed'), 1200);
    return () => window.clearTimeout(timer);
  }, [cvStatus]);
  function selectJob(id: string) {
    if (!jobs.some(job => job.id === id) || id === selectedJobId) return;
    setSelectedJobId(id);
    setInterviewCompleted(false);
    setSentAnswers([]);
  }
  function applyToJob(id: string) {
    if (cvStatus !== 'analysed' || (applications[id] ?? 'available') !== 'available') return;
    updateApplication(id, 'applied');
    selectJob(id);
  }
  function nominateJob(id: string) {
    updateApplication(id, 'nominated');
  }
  function completeTrainingQuestion(jobId: string, questionIndex: number) {
    if (!jobs.some(job => job.id === jobId)) return;
    setTrainingProgress(current => recordTrainingQuestion(current, jobId, questionIndex));
  }
  function reviewPlan(id: string) {
    setReviewedPlans(current => current.includes(id) ? current : [...current, id]);
  }
  function setJobPreferences(id: string, values: string[]) {
    if (!jobs.some(job => job.id === id)) return;
    const allowed = new Set<string>(communicationPreferences.map(item => item.id));
    setPreferences(current => ({ ...current, [id]: [...new Set(values.filter(value => allowed.has(value)))] }));
  }
  function setAdditionalCommunicationNeeds(id: string, value: string) {
    if (!jobs.some(job => job.id === id)) return;
    setAdditionalNeeds(current => ({ ...current, [id]: value }));
  }
  function finishInterview(questions?: string[], durationSeconds = 0) {
    if (!['nominated', 'scheduled'].includes(applications[selectedJobId] ?? '')) return;
    setInterviewCompleted(true);
    updateApplication(selectedJobId, 'completed');
    setReports(current => [{ id: `session-${Date.now()}`, jobId: selectedJobId, date: new Date().toISOString(), answers: [...sentAnswers], questions: questions ? [...questions] : [], durationSeconds }, ...current]);
    setSentAnswers([]);
  }
  return <SanadContext.Provider value={{ termsAccepted, setTermsAccepted, trainingConsent, setTrainingConsent, darkMode, setDarkMode, candidateName, candidateEmail, signedIn, signIn, updateProfile, signOut, guideOpen, openGuide: () => setGuideOpen(true), closeGuide: () => setGuideOpen(false), schedules, scheduleInterview, applicationDates, applicationHistory, updateApplication, jobSkills, setJobSkills: (id, skills) => setSkills(current => ({ ...current, [id]: skills })), selectedJobId, selectJob, cvName, setCvName, cvStatus, setCvStatus, applications, applyToJob, nominateJob, reviewedPlans, reviewPlan, preferences, setJobPreferences, additionalCommunicationNeeds, setAdditionalCommunicationNeeds, now, reports, finishInterview, interpreterRequested, setInterpreterRequested, practiceCompleted, trainingProgress, completeTrainingQuestion, interviewCompleted, setInterviewCompleted, sentAnswers, setSentAnswers }}>{children}</SanadContext.Provider>;
}
export function useSanad() {
  const context = useContext(SanadContext);
  if (!context) throw new Error('SanadProvider is required');
  return context;
}