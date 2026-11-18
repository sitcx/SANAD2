import { describe, expect, it } from 'vitest';
import { getApplicationProgress } from '@/lib/application-progress';
import { workspaceNavigation } from '@/lib/workspace-navigation';

describe('Focused candidate navigation', () => {
  it('contains only the dashboard destination; tracking remains within the dashboard', () => {
    expect(workspaceNavigation.map(item => item.to)).toEqual(['/dashboard']);
  });
});

describe('Visual application progress', () => {
  const history = [
    { status: 'applied' as const, date: '2026-11-12T09:00:00+03:00' },
    { status: 'reviewing' as const, date: '2026-11-13T09:00:00+03:00' },
    { status: 'nominated' as const, date: '2026-11-14T09:00:00+03:00' },
  ] as const;
  it('distinguishes completed, current and upcoming stages with real recorded dates', () => {
    expect(getApplicationProgress('nominated', history)).toEqual([
      { status: 'applied', state: 'completed', date: history[0].date },
      { status: 'reviewing', state: 'completed', date: history[1].date },
      { status: 'nominated', state: 'current', date: history[2].date },
      { status: 'scheduled', state: 'upcoming', date: undefined },
      { status: 'completed', state: 'upcoming', date: undefined },
      { status: 'accepted', state: 'upcoming', date: undefined },
    ]);
  });
  it('does not mark a skipped interview as completed when a direct offer arrives', () => {
    const progress = getApplicationProgress('accepted', [...history, { status: 'accepted', date: '2026-11-17T10:00:00+03:00' }]);
    expect(progress.find(step => step.status === 'scheduled')?.state).toBe('skipped');
    expect(progress.find(step => step.status === 'completed')?.state).toBe('skipped');
    expect(progress.find(step => step.status === 'accepted')?.state).toBe('current');
  });
  it.each(['rejected', 'withdrawn'] as const)('ends the timeline at %s instead of promising future stages', status => {
    const progress = getApplicationProgress(status, [...history, { status, date: '2026-11-17T10:00:00+03:00' }]);
    expect(progress.map(step => step.status)).toEqual(['applied', 'reviewing', 'nominated', status]);
    expect(progress.at(-1)?.state).toBe('current');
    expect(progress.some(step => step.state === 'upcoming')).toBe(false);
  });
});