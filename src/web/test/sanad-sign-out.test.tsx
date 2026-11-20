import { act, renderHook } from '@testing-library/react';
import { useEffect, useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

describe('Simulated candidate sign-out', () => {
  it('ends sign-in and resets candidate identity before another candidate enters', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.signIn('سارة'));
    expect(result.current.signedIn).toBe(true);
    act(() => result.current.signOut());
    expect(result.current.signedIn).toBe(false);
    expect(result.current.candidateName).toBe('أحمد');
    act(() => result.current.signIn('نورة'));
    expect(result.current.signedIn).toBe(true);
    expect(result.current.candidateName).toBe('نورة');
  });

  it('removes candidate preferences, consent, CV changes, applications, appointments and reports', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    const initial = result.current;
    act(() => {
      result.current.signIn('سارة');
      result.current.setTermsAccepted(true);
      result.current.setTrainingConsent(true);
      result.current.setJobPreferences('analyst', ['sign', 'other']);
      result.current.setAdditionalCommunicationNeeds('analyst', 'إضاءة واضحة');
      result.current.setCvName('سارة.pdf');
      result.current.setCvStatus('uploaded');
      for (let index = 0; index < 8; index++) result.current.completeTrainingQuestion('analyst', index);
      result.current.setInterpreterRequested(true);
      result.current.reviewPlan('analyst');
      result.current.setJobSkills('analyst', ['مهارة معدلة']);
      result.current.scheduleInterview('analyst', '2026-11-20T13:00:00+03:00');
      result.current.setSentAnswers(['إجابة سارة المعتمدة']);
    });
    act(() => result.current.finishInterview(['سؤال سارة'], 60));
    expect(result.current.reports[0]?.answers).toEqual(['إجابة سارة المعتمدة']);
    act(() => result.current.signOut());
    expect(result.current.preferences).toEqual({});
    expect(result.current.additionalCommunicationNeeds).toEqual({});
    expect(result.current.termsAccepted).toBe(false);
    expect(result.current.trainingConsent).toBe(false);
    expect(result.current.cvName).toBe(initial.cvName);
    expect(result.current.cvStatus).toBe('analysed');
    expect(result.current.reviewedPlans).toEqual([]);
    expect(result.current.jobSkills).toEqual({});
    expect(result.current.schedules).toEqual(initial.schedules);
    expect(result.current.applications).toEqual(initial.applications);
    expect(result.current.applicationHistory).toEqual(initial.applicationHistory);
    expect(result.current.applicationDates).toEqual(initial.applicationDates);
    expect(result.current.reports).toEqual(initial.reports);
    expect(result.current.sentAnswers).toEqual([]);
    expect(result.current.interviewCompleted).toBe(false);
    expect(result.current.practiceCompleted).toBe(false);
    expect(result.current.trainingProgress).toEqual({});
    expect(result.current.interpreterRequested).toBe(false);
    expect(result.current.guideOpen).toBe(false);
  });

  it('unmounts old child views and resets local drafts on sign-out', () => {
    const cleanup = vi.fn();
    const { result } = renderHook(() => {
      const state = useSanad();
      const [draft, setDraft] = useState('');
      useEffect(() => cleanup, []);
      return { state, draft, setDraft };
    }, { wrapper: SanadProvider });
    act(() => result.current.setDraft('مسودة محلية خاصة'));
    expect(result.current.draft).toBe('مسودة محلية خاصة');
    act(() => result.current.state.signOut());
    expect(cleanup).toHaveBeenCalledTimes(1);
    expect(result.current.draft).toBe('');
  });
});