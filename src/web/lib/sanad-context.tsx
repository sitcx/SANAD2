import { useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { canUpdateApplication, communicationPreferences, scheduleConflict, interviewSchedules, jobs, previousReports, type ApplicationStatus, type CvStatus, type InterviewReport } from './sanad-data';
import { SanadContext } from './sanad-state';
import type { CareerTrackId } from './career-discovery';
import { candidatePool, SELF_ID, type CompanyJob } from './company';
import { candidateApi } from './company-api';
import type { AccountRole } from './sanad-state';
import { advanceTicket, createTicket, rateTicket, type CommunicationMode, type SupportCategory, type SupportTicket } from './support-tickets';
// Unit tests run without the API server.
const syncEnabled = import.meta.env.MODE !== 'test';
export function SanadProvider({ children }: { children: ReactNode }) {
  const [sessionKey, setSessionKey] = useState(0);
  const signOut = useCallback(() => setSessionKey(current => current + 1), []);
  return <SanadSessionProvider key={sessionKey} signOut={signOut}>{children}</SanadSessionProvider>;
}

function SanadSessionProvider({ children, signOut }: { children: ReactNode; signOut: () => void }) {
  const [candidateName, setCandidateName] = useState('أحمد');
  const [candidateEmail, setCandidateEmail] = useState('');
  const [signedIn, setSignedIn] = useState(false);
  const [communicationMode, setCommunicationMode] = useState<CommunicationMode>('sign');
  const [role, setRole] = useState<AccountRole>('candidate');
  const [companyName, setCompanyName] = useState('شركة بُعد التقنية');
  const [companyJobs, setCompanyJobs] = useState<CompanyJob[]>([]);
  const [jobMinYears, setMinYears] = useState<Record<string, number>>({ analyst: 1, support: 1, designer: 1 });
  const [poolApplications, setPoolApplications] = useState<Record<string, Record<string, ApplicationStatus>>>(() => Object.fromEntries(candidatePool.map(candidate => [candidate.id, { ...candidate.applications }])));
  const [poolSchedules, setPoolSchedules] = useState<Record<string, string>>({});
  const [careerTrack, setCareerTrack] = useState<CareerTrackId | null>(null);
  const [careerDecided, setCareerDecided] = useState(false);
  const [supportTickets, setSupportTickets] = useState<SupportTicket[]>([]);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [trainingConsent, setTrainingConsent] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [largeText, setLargeText] = useState(false);
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
  const [interviewCompleted, setInterviewCompleted] = useState(false);
  const [sentAnswers, setSentAnswers] = useState<string[]>([]);
  useEffect(() => {
    document.documentElement.classList.toggle('a11y-large', largeText);
    return () => document.documentElement.classList.remove('a11y-large');
  }, [largeText]);
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    return () => document.documentElement.classList.remove('dark');
  }, [darkMode]);
  useEffect(() => {
    if (!syncEnabled) return;
    let active = true;
    candidateApi.applications().then(rows => { if (active) rows.forEach(row => syncSelfApplication(row.posting_id, row.status, row.interview_at)); }).catch(() => undefined);
    return () => { active = false; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  function signIn(name: string, email = '', mode?: CommunicationMode, account: AccountRole = 'candidate') {
    if (!name.trim()) return;
    if (account === 'company') setCompanyName(name.trim()); else setCandidateName(name.trim());
    setCandidateEmail(email.trim()); if (mode) setCommunicationMode(mode); setRole(account); setSignedIn(true);
  }
  function addCompanyJob(title: string, skills: string[], minYears: number) {
    const cleanSkills = [...new Set(skills.map(skill => skill.trim()).filter(Boolean))];
    if (!title.trim()) return 'اكتب المسمى الوظيفي.';
    if (!cleanSkills.length) return 'أضف مهارة مطلوبة واحدة على الأقل.';
    const id = `job-${Date.now()}`;
    setCompanyJobs(current => [...current, { id, title: title.trim(), skills: cleanSkills, minYears, custom: true }]);
    setMinYears(current => ({ ...current, [id]: minYears }));
    return null;
  }
  function companyUpdateCandidate(candidateId: string, jobId: string, status: ApplicationStatus) {
    if (candidateId === SELF_ID) { updateApplication(jobId, status); return; }
    const current = poolApplications[candidateId]?.[jobId] ?? 'available';
    if (current !== 'available' ? !canUpdateApplication(current, status) : status !== 'nominated') return;
    setPoolApplications(all => ({ ...all, [candidateId]: { ...all[candidateId], [jobId]: status } }));
  }
  function companySchedule(candidateId: string, jobId: string, date: string) {
    if (!Number.isFinite(Date.parse(date))) return 'اختر موعدًا صحيحًا.';
    if (candidateId === SELF_ID) {
      const error = scheduleInterview(jobId, date);
      if (error) return error;
      updateApplication(jobId, 'scheduled');
      return null;
    }
    setPoolSchedules(all => ({ ...all, [`${candidateId}:${jobId}`]: date }));
    companyUpdateCandidate(candidateId, jobId, 'scheduled');
    return null;
  }
  function completeCareerDiscovery(track: CareerTrackId) { setCareerTrack(track); setCareerDecided(true); }
  function acceptOffer(id: string) { if (applications[id] === 'accepted') updateApplication(id, 'hired'); }
  const hiredJobId = jobs.find(job => applications[job.id] === 'hired')?.id;
  function submitSupportTicket(category: SupportCategory, details: string) {
    if (!hiredJobId) return false;
    const ticket = createTicket(`ticket-${Date.now()}`, hiredJobId, category, details, new Date().toISOString());
    if (!ticket) return false;
    setSupportTickets(current => [ticket, ...current]);
    return true;
  }
  function rateSupportTicket(id: string, rating: number) {
    setSupportTickets(current => current.map(ticket => ticket.id === id ? rateTicket(ticket, rating) : ticket));
  }
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
    if (syncEnabled && ['applied', 'completed', 'hired', 'withdrawn'].includes(status)) candidateApi.setStatus(id, status).catch(() => undefined);
  }
  function syncSelfApplication(id: string, status: ApplicationStatus, interviewAt?: string | null) {
    if (!jobs.some(job => job.id === id)) return;
    const date = new Date().toISOString();
    setApplications(current => current[id] === status ? current : ({ ...current, [id]: status }));
    setApplicationHistory(current => (current[id] ?? []).at(-1)?.status === status ? current : ({ ...current, [id]: [...(current[id] ?? []), { status, date }] }));
    if (interviewAt) setSchedules(current => ({ ...current, [id]: interviewAt }));
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
  const openTicketKey = supportTickets.filter(ticket => ticket.status !== 'resolved').map(ticket => `${ticket.id}:${ticket.status}`).join('|');
  useEffect(() => {
    if (!openTicketKey) return;
    const timer = window.setTimeout(() => setSupportTickets(current => current.map(ticket => ticket.status === 'resolved' ? ticket : advanceTicket(ticket, new Date().toISOString()))), 4000);
    return () => window.clearTimeout(timer);
  }, [openTicketKey]);
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
  return <SanadContext.Provider value={{ termsAccepted, setTermsAccepted, trainingConsent, setTrainingConsent, darkMode, setDarkMode, largeText, setLargeText, candidateName, candidateEmail, signedIn, signIn, role, switchRole: setRole, companyName, companyJobs, addCompanyJob, jobMinYears, setJobMinYears: (id, years) => setMinYears(current => ({ ...current, [id]: years })), poolApplications, poolSchedules, companyUpdateCandidate, companySchedule, syncSelfApplication, communicationMode, setCommunicationMode, careerTrack, careerDecided, completeCareerDiscovery, skipCareerDiscovery: () => setCareerDecided(true), acceptOffer, supportTickets, submitSupportTicket, rateSupportTicket, updateProfile, signOut, guideOpen, openGuide: () => setGuideOpen(true), closeGuide: () => setGuideOpen(false), schedules, scheduleInterview, applicationDates, applicationHistory, updateApplication, jobSkills, setJobSkills: (id, skills) => setSkills(current => ({ ...current, [id]: skills })), selectedJobId, selectJob, cvName, setCvName, cvStatus, setCvStatus, applications, applyToJob, nominateJob, reviewedPlans, reviewPlan, preferences, setJobPreferences, additionalCommunicationNeeds, setAdditionalCommunicationNeeds, now, reports, finishInterview, interpreterRequested, setInterpreterRequested, interviewCompleted, setInterviewCompleted, sentAnswers, setSentAnswers }}>{children}</SanadContext.Provider>;
}
export function useSanad() {
  const context = useContext(SanadContext);
  if (!context) throw new Error('SanadProvider is required');
  return context;
}