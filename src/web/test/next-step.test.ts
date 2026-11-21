import { describe, expect, it } from 'vitest';
import { nextStep } from '@/lib/next-step';

const base = { cvName: 'cv.pdf', cvStatus: 'analysed' as const, applications: {}, schedules: {}, now: Date.parse('2026-11-21T09:00:00+03:00') };

describe('candidate next step', () => {
  it('asks for a CV first, then to apply', () => {
    expect(nextStep({ ...base, cvName: '' }).kind).toBe('cv');
    expect(nextStep({ ...base, cvStatus: 'analysing' }).kind).toBe('cv');
    expect(nextStep(base).kind).toBe('apply');
  });
  it('follows the application from review to the soonest interview', () => {
    expect(nextStep({ ...base, applications: { designer: 'applied' } }).kind).toBe('review');
    const soon = nextStep({ ...base, applications: { analyst: 'nominated', support: 'scheduled' }, schedules: { analyst: '2026-11-27T10:00:00+03:00', support: '2026-11-24T10:00:00+03:00' } });
    expect(soon).toMatchObject({ kind: 'interview-soon', jobId: 'support', preview: true });
    const now = nextStep({ ...base, applications: { analyst: 'scheduled' }, schedules: { analyst: '2026-11-21T08:00:00+03:00' } });
    expect(now).toMatchObject({ kind: 'interview-now', jobId: 'analyst' });
  });
  it('puts the offer and post-hire support ahead of everything else', () => {
    expect(nextStep({ ...base, applications: { analyst: 'completed' } }).kind).toBe('decision');
    expect(nextStep({ ...base, applications: { analyst: 'accepted', support: 'applied' } }).kind).toBe('offer');
    expect(nextStep({ ...base, applications: { analyst: 'hired', support: 'accepted' } })).toMatchObject({ kind: 'support', to: '/support' });
  });
});
