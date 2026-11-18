import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SanadProvider, useSanad } from '@/lib/sanad-context';
import { getTrainingReadiness, recordTrainingQuestion } from '@/lib/training-readiness';

describe('Per-job training readiness', () => {
  it('starts at zero before training', () => {
    expect(getTrainingReadiness()).toBe(0);
  });

  it('updates from completed questions and reaches 100 only after all eight', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    const percentages = [13, 25, 38, 50, 63, 75, 88, 100];
    percentages.forEach((percentage, index) => {
      act(() => result.current.completeTrainingQuestion('analyst', index));
      expect(getTrainingReadiness(result.current.trainingProgress['analyst'])).toBe(percentage);
      expect(result.current.practiceCompleted).toBe(index === 7);
    });
  });

  it('keeps each job independent and retains its readiness after switching jobs', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.completeTrainingQuestion('analyst', 0));
    act(() => result.current.selectJob('support'));
    expect(getTrainingReadiness(result.current.trainingProgress['support'])).toBe(0);
    act(() => {
      result.current.completeTrainingQuestion('support', 0);
      result.current.completeTrainingQuestion('support', 1);
    });
    act(() => result.current.selectJob('analyst'));
    expect(getTrainingReadiness(result.current.trainingProgress['analyst'])).toBe(13);
    expect(getTrainingReadiness(result.current.trainingProgress['support'])).toBe(25);
    expect(getTrainingReadiness(result.current.trainingProgress['designer'])).toBe(0);
  });

  it('does not inflate readiness when the same question is retried', () => {
    const progress = recordTrainingQuestion({}, 'analyst', 0);
    expect(recordTrainingQuestion(progress, 'analyst', 0)).toBe(progress);
    expect(getTrainingReadiness([0, 0, 0])).toBe(13);
  });

  it('does not credit missing or invalid questions', () => {
    expect(recordTrainingQuestion({}, 'analyst', 8)).toEqual({});
    expect(recordTrainingQuestion({}, 'analyst', -1)).toEqual({});
    expect(recordTrainingQuestion({}, 'analyst', 0.5)).toEqual({});
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.completeTrainingQuestion('missing-job', 0));
    expect(result.current.trainingProgress).toEqual({});
  });

  it('derives the dashboard training step from the currently selected job', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => {
      for (let index = 0; index < 8; index++) result.current.completeTrainingQuestion('analyst', index);
    });
    expect(result.current.practiceCompleted).toBe(true);
    act(() => result.current.selectJob('support'));
    expect(result.current.practiceCompleted).toBe(false);
    act(() => result.current.selectJob('analyst'));
    expect(result.current.practiceCompleted).toBe(true);
  });

  it('resets all job readiness on sign-out', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.completeTrainingQuestion('analyst', 0));
    act(() => result.current.signOut());
    expect(getTrainingReadiness(result.current.trainingProgress['analyst'])).toBe(0);
  });
});