import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useApplicationJourney } from '@/hooks/use-application-journey';
import { getApplicationProgress } from '@/lib/application-progress';

const history = [
  { status: 'applied' as const, date: '2026-11-12T09:00:00+03:00' },
  { status: 'reviewing' as const, date: '2026-11-13T09:00:00+03:00' },
  { status: 'nominated' as const, date: '2026-11-14T09:00:00+03:00' },
];
const nominated = getApplicationProgress('nominated', history);

describe('Application journey timing and lifecycle', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

  it('finishes at the saved nominated stage and cancels timers on exit', () => {
    const { result, unmount } = renderHook(() => useApplicationJourney(nominated, false));
    act(() => vi.advanceTimersByTime(160));
    expect(result.current.steps[0]?.node).toBe('visible');
    expect(result.current.steps[1]?.node).toBe('hidden');
    act(() => vi.advanceTimersByTime(500));
    expect(result.current.steps[0]?.node).toBe('checked');
    act(() => vi.advanceTimersByTime(300));
    expect(result.current.steps[0]?.connector).toBe('drawing');
    act(() => vi.advanceTimersByTime(4000));
    expect(result.current.steps.map(step => step.node)).toEqual(['checked', 'checked', 'active', 'muted', 'muted', 'muted']);
    expect(result.current.settled).toBe(true);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('waits while the introductory guide obscures the timeline', () => {
    const { result, rerender, unmount } = renderHook(({ paused }) => useApplicationJourney(nominated, paused), { initialProps: { paused: true } });
    act(() => vi.advanceTimersByTime(10000));
    expect(result.current.steps.every(step => step.node === 'hidden')).toBe(true);
    rerender({ paused: false });
    act(() => vi.advanceTimersByTime(160));
    expect(result.current.steps[0]?.node).toBe('visible');
    unmount();
  });

  it('replaces an in-flight journey when the shared application becomes withdrawn', () => {
    const { result, rerender, unmount } = renderHook(({ progress }) => useApplicationJourney(progress, false), { initialProps: { progress: nominated } });
    act(() => vi.advanceTimersByTime(960));
    const withdrawn = getApplicationProgress('withdrawn', [...history, { status: 'withdrawn', date: '2026-11-17T09:00:00+03:00' }]);
    rerender({ progress: withdrawn });
    act(() => vi.advanceTimersByTime(10000));
    expect(result.current.steps.map(step => step.node)).toEqual(['checked', 'checked', 'checked', 'active']);
    expect(result.current.steps.at(-1)?.connector).toBe('hidden');
    expect(vi.getTimerCount()).toBe(0);
    unmount();
  });

  it('shows saved states immediately without timers when reduced motion is requested', () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true, addEventListener: () => {}, removeEventListener: () => {} } as unknown as MediaQueryList);
    const { result, unmount } = renderHook(() => useApplicationJourney(nominated, false));
    expect(result.current.steps.map(step => step.node)).toEqual(['checked', 'checked', 'active', 'muted', 'muted', 'muted']);
    expect(result.current.settled).toBe(true);
    expect(vi.getTimerCount()).toBe(0);
    unmount();
  });
});