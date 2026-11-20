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
  it('finishes mock CV analysis in shared session state', () => {
    vi.useFakeTimers();
    try {
      const { result, unmount } = renderHook(() => useSanad(), { wrapper: SanadProvider });
      act(() => result.current.setCvStatus('analysing'));
      expect(result.current.cvStatus).toBe('analysing');
      act(() => vi.advanceTimersByTime(1200));
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
  it('keeps only approved answers in the report for the completed interview', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    const draft = 'مسودة لم أعتمدها';
    const approved = approveAnswer('أستخدم المحادثة لحل مشكلات العملاء', true);
    expect(approveAnswer(draft, false)).toBeNull();
    act(() => result.current.selectJob('support'));
    if (approved === null) throw new Error('Expected approved answer');
    act(() => result.current.setSentAnswers([approved]));
    act(() => result.current.finishInterview());
    expect(result.current.reports[0]?.jobId).toBe('support');
    expect(result.current.reports[0]?.answers).toEqual(['أستخدم المحادثة لحل مشكلات العملاء']);
    expect(result.current.reports[0]?.answers).not.toContain(draft);
    expect(result.current.sentAnswers).toEqual([]);
    expect(result.current.applications['support']).toBe('completed');
    act(() => result.current.selectJob('designer'));
    expect(result.current.sentAnswers).toEqual([]);
    expect(result.current.interviewCompleted).toBe(false);
    expect(result.current.reports[0]?.answers).toEqual(['أستخدم المحادثة لحل مشكلات العملاء']);
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
  it('snapshots approved questions and measured duration with the answers', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.selectJob('support'));
    act(() => result.current.setSentAnswers(['حللت مشكلة العميل في CRM.']));
    act(() => result.current.finishInterview(['كيف ساعدت العميل؟'], 95));
    expect(result.current.reports[0]?.questions).toEqual(['كيف ساعدت العميل؟']);
    expect(result.current.reports[0]?.durationSeconds).toBe(95);
    act(() => result.current.updateApplication('support', 'accepted'));
    expect(result.current.applications['support']).toBe('accepted');
  });
});