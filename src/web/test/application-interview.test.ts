import { describe, expect, it } from 'vitest';
import { getApplicationInterview } from '@/lib/application-interview';

describe('Shared interview appointment in application tracking', () => {
  it.each(['nominated', 'scheduled'] as const)('uses the shared appointment rather than a stage-history date for %s', status => {
    expect(getApplicationInterview(status, '2026-11-17T10:00:00+03:00')).toBe('2026-11-17T10:00:00+03:00');
    expect(getApplicationInterview(status, '2026-11-19T13:30:00+03:00')).toBe('2026-11-19T13:30:00+03:00');
  });
  it.each(['applied', 'reviewing', 'rejected', 'withdrawn', 'accepted', 'completed'] as const)('does not imply an upcoming appointment for %s', status => {
    expect(getApplicationInterview(status, '2026-11-17T10:00:00+03:00')).toBeNull();
  });
  it('does not invent dates for missing or invalid appointments', () => {
    expect(getApplicationInterview('scheduled', undefined)).toBeNull();
    expect(getApplicationInterview('scheduled', 'invalid')).toBeNull();
  });
});