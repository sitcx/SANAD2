import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SanadProvider, useSanad } from '@/lib/sanad-context';
import { approveAnswer } from '@/lib/sanad-data';

describe('Candidate session journey', () => {
  it('keeps optional training consent separate from terms acceptance and revocable', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    expect(result.current.trainingConsent).toBe(false);
    act(() => result.current.setTermsAccepted(true));
    expect(result.current.trainingConsent).toBe(false);
    act(() => result.current.setTrainingConsent(true));
    act(() => result.current.setTrainingConsent(false));
    expect(result.current.trainingConsent).toBe(false);
    expect(result.current.termsAccepted).toBe(true);
  });
  it('does not change the schedule when another interview already uses that day', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    let error: string | null = null;
    act(() => { error = result.current.scheduleInterview('support', '2026-11-20T15:00:00+03:00'); });
    expect(error).not.toBeNull();
    expect(result.current.schedules['support']).toBe('2026-11-22T10:00:00+03:00');
  });
  it('keeps the CV analysing until the job agent answers', () => {
    vi.useFakeTimers();
    try {
      const { result, unmount } = renderHook(() => useSanad(), { wrapper: SanadProvider });
      act(() => result.current.setCvStatus('analysing'));
      act(() => vi.advanceTimersByTime(5000));
      expect(result.current.cvStatus).toBe('analysing');
      act(() => result.current.setCvStatus('analysed'));
      expect(result.current.cvStatus).toBe('analysed');
      unmount();
    } finally {
      vi.useRealTimers();
    }
  });
  it('requires CV analysis before applying to an available job', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.setCvStatus('uploaded'));
    act(() => result.current.applyToJob('designer'));
    expect(result.current.applications['designer']).toBe('available');
    act(() => result.current.setCvStatus('analysed'));
    act(() => result.current.applyToJob('designer'));
    expect(result.current.applications['designer']).toBe('applied');
    expect(result.current.selectedJobId).toBe('designer');
  });
  it('requires an application before simulated nomination', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.nominateJob('designer'));
    expect(result.current.applications['designer']).toBe('available');
    act(() => result.current.applyToJob('designer'));
    act(() => result.current.nominateJob('designer'));
    expect(result.current.applications['designer']).toBe('nominated');
  });
  it('keeps accommodation preferences separate for each job', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.setJobPreferences('designer', ['text', 'hearing-aid']));
    act(() => result.current.setJobPreferences('analyst', ['sign']));
    expect(result.current.preferences['designer']).toEqual(['text', 'hearing-aid']);
    expect(result.current.preferences['analyst']).toEqual(['sign']);
  });
  it('ends the interview by waiting for the company decision', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    expect(approveAnswer('مسودة لم أعتمدها', false)).toBeNull();
    act(() => result.current.selectJob('support'));
    act(() => result.current.setSentAnswers(['أستخدم المحادثة لحل مشكلات العملاء']));
    act(() => result.current.finishInterview());
    expect(result.current.applications['support']).toBe('completed');
    expect(result.current.interviewCompleted).toBe(true);
    expect(result.current.sentAnswers).toEqual([]);
    act(() => result.current.selectJob('designer'));
    expect(result.current.interviewCompleted).toBe(false);
  });
  it('records application dates and updates in the linked tracker', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.applyToJob('designer'));
    expect(Number.isFinite(Date.parse(result.current.applicationDates['designer'] ?? ''))).toBe(true);
    act(() => result.current.updateApplication('designer', 'reviewing'));
    act(() => result.current.nominateJob('designer'));
    expect(result.current.applicationHistory['designer']?.map(item => item.status)).toEqual(['applied', 'reviewing', 'nominated']);
  });
  it('shares employer scheduling and skill changes throughout the session', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.scheduleInterview('support', '2026-11-22T11:00:00+03:00'));
    act(() => result.current.setJobSkills('support', ['CRM', 'التواصل الكتابي']));
    expect(result.current.schedules['support']).toBe('2026-11-22T11:00:00+03:00');
    expect(result.current.jobSkills['support']).toEqual(['CRM', 'التواصل الكتابي']);
  });
  it('lets the company accept after the interview', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.selectJob('support'));
    act(() => result.current.finishInterview());
    act(() => result.current.updateApplication('support', 'accepted'));
    expect(result.current.applications['support']).toBe('accepted');
  });
});