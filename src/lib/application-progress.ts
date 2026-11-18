import type { ApplicationStatus } from './sanad-data';

export const applicationProgressStages = ['applied', 'reviewing', 'nominated', 'scheduled', 'completed', 'accepted'] as const;
export type ProgressState = 'completed' | 'current' | 'upcoming' | 'skipped';
export type ApplicationEvent = { status: ApplicationStatus; date: string };

/** Presentation only: never infer completed events or dates from a later status. */
export function getApplicationProgress(status: ApplicationStatus, history: readonly ApplicationEvent[]) {
  if (status === 'available') return [];
  const ended = status === 'rejected' || status === 'withdrawn';
  const currentIndex = applicationProgressStages.findIndex(stage => stage === status);
  const lastRecordedIndex = history.reduce((last, event) => Math.max(last, applicationProgressStages.findIndex(stage => stage === event.status)), -1);
  const position = ended ? lastRecordedIndex : currentIndex;
  const stages: ApplicationStatus[] = ended ? [...applicationProgressStages.slice(0, position + 1), status] : [...applicationProgressStages];
  return stages.map((stage, index) => {
    const event = [...history].reverse().find(item => item.status === stage);
    const state: ProgressState = stage === status ? 'current' : event ? 'completed' : index < position ? 'skipped' : 'upcoming';
    return { status: stage, state, date: event?.date };
  });
}