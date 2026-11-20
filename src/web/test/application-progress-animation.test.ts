import { describe, expect, it } from 'vitest';
import { getApplicationProgress } from '@/lib/application-progress';
import { getApplicationJourney, getSettledJourney } from '@/lib/application-progress-animation';

const history = [
  { status: 'applied' as const, date: '2026-11-12T09:00:00+03:00' },
  { status: 'reviewing' as const, date: '2026-11-13T09:00:00+03:00' },
  { status: 'nominated' as const, date: '2026-11-14T09:00:00+03:00' },
];

describe('Recorded application journey animation', () => {
  it('reveals the first icon, then its check, then the connector before the second icon', () => {
    const frames = getApplicationJourney(getApplicationProgress('nominated', history));
    const firstReveal = frames.findIndex(frame => frame.steps[0]?.node === 'visible');
    const firstCheck = frames.findIndex(frame => frame.steps[0]?.node === 'checked');
    const firstLine = frames.findIndex(frame => frame.steps[0]?.connector === 'drawing');
    const secondReveal = frames.findIndex(frame => frame.steps[1]?.node === 'visible');
    expect(firstReveal).toBeGreaterThan(0);
    expect(firstCheck).toBeGreaterThan(firstReveal);
    expect(firstLine).toBeGreaterThan(firstCheck);
    expect(secondReveal).toBeGreaterThan(firstLine);
    const revealFrame = frames[secondReveal];
    const lineFrame = frames[firstLine];
    if (!revealFrame || !lineFrame) throw new Error('Missing sequential frames');
    expect(revealFrame.delay - lineFrame.delay).toBe(800);
  });
  it('activates only the saved nominated stage and never checks or advances into future stages', () => {
    const frames = getApplicationJourney(getApplicationProgress('nominated', history));
    expect(frames.at(-1)?.steps.map(step => step.node)).toEqual(['checked', 'checked', 'active', 'muted', 'muted', 'muted']);
    expect(frames.every(frame => frame.steps.slice(3).every(step => step.node !== 'checked' && step.node !== 'active' && step.connector !== 'drawing'))).toBe(true);
    expect(frames.every(frame => frame.steps[2]?.connector !== 'drawing')).toBe(true);
  });
  it('continues a saved forward update from the previous active stage rather than replaying completed stages', () => {
    const previous = getApplicationProgress('nominated', history);
    const updated = getApplicationProgress('scheduled', [...history, { status: 'scheduled', date: '2026-11-17T09:00:00+03:00' }]);
    const frames = getApplicationJourney(updated, previous);
    expect(frames[0]?.steps.map(step => step.node)).toEqual(['checked', 'checked', 'visible', 'hidden', 'hidden', 'hidden']);
    expect(frames.at(-1)?.steps.map(step => step.node)).toEqual(['checked', 'checked', 'checked', 'active', 'muted', 'muted']);
  });
  it('never assigns a check to stages absent from the saved history', () => {
    const frames = getApplicationJourney(getApplicationProgress('accepted', [...history, { status: 'accepted', date: '2026-11-17T09:00:00+03:00' }]));
    expect(frames.every(frame => frame.steps[3]?.node !== 'checked' && frame.steps[4]?.node !== 'checked')).toBe(true);
    expect(frames.at(-1)?.steps.map(step => step.node)).toEqual(['checked', 'checked', 'checked', 'muted', 'muted', 'active']);
  });
  it.each(['rejected', 'withdrawn'] as const)('stops at the saved %s outcome without future stages', status => {
    const progress = getApplicationProgress(status, [...history, { status, date: '2026-11-17T09:00:00+03:00' }]);
    const frames = getApplicationJourney(progress);
    expect(frames.at(-1)?.steps.map(step => step.node)).toEqual(['checked', 'checked', 'checked', 'active']);
    expect(frames.at(-1)?.steps.at(-1)?.connector).toBe('hidden');
    expect(getSettledJourney(progress)).toEqual(frames.at(-1)?.steps);
  });
});