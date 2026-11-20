import type { ApplicationStatus } from './sanad-data';

/** A shared appointment is visible only after nomination and before terminal outcomes. */
export function getApplicationInterview(status: ApplicationStatus, schedule: string | undefined): string | null {
  if (!['nominated', 'scheduled'].includes(status) || !schedule || !Number.isFinite(Date.parse(schedule))) return null;
  return schedule;
}