import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { candidatePool, companyActions, companyIndicators, matchScore, rankCandidates, SELF_ID, type CompanyJob } from '@/lib/company';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

const wrapper = ({ children }: { children: ReactNode }) => <SanadProvider>{children}</SanadProvider>;
const analyst: CompanyJob = { id: 'analyst', title: 'محلل بيانات', skills: ['Excel', 'SQL', 'تحليل البيانات'], minYears: 0 };

describe('company candidate filtering', () => {
  it('scores the share of required skills', () => {
    expect(matchScore({ skills: ['excel', 'SQL'] }, ['Excel', 'SQL', 'تحليل البيانات'])).toBe(67);
    expect(matchScore({ skills: [] }, [])).toBe(0);
  });
  it('lists only applicants, ranked by match', () => {
    const ranked = rankCandidates(analyst, candidatePool, { minYears: 0, mustHave: [] });
    expect(ranked.map(item => item.candidate.id)).toEqual(['c1', 'c4', 'c8', 'c2']);
  });
  it('filters by years of experience and must-have skills', () => {
    expect(rankCandidates(analyst, candidatePool, { minYears: 3, mustHave: [] }).map(item => item.candidate.id)).toEqual(['c1', 'c4', 'c8']);
    expect(rankCandidates(analyst, candidatePool, { minYears: 0, mustHave: ['SQL'] }).map(item => item.candidate.id)).toEqual(['c1', 'c4']);
  });
  it('suggests matching pool candidates for a new job without applicants', () => {
    const job: CompanyJob = { id: 'job-x', title: 'مدخل بيانات', skills: ['Excel'], minYears: 0, custom: true };
    expect(rankCandidates(job, candidatePool, { minYears: 0, mustHave: [] }).map(item => item.candidate.id).sort()).toEqual(['c1', 'c2', 'c8']);
  });
  it('computes indicators including retention after hiring', () => {
    const indicators = companyIndicators([analyst], candidatePool);
    expect(indicators).toMatchObject({ applicants: 4, hired: 2, retention: 50 });
  });
  it('offers the next company step per status', () => {
    expect(companyActions('applied')).toEqual(['nominate', 'reject']);
    expect(companyActions('completed')).toEqual(['accept', 'reject']);
    expect(companyActions('hired')).toEqual([]);
  });
});

describe('company and candidate share one journey', () => {
  it('nominates, schedules and accepts the candidate, who then becomes hired', () => {
    const { result } = renderHook(() => useSanad(), { wrapper });
    act(() => result.current.signIn('شركة بُعد', 'hr@example.com', undefined, 'company'));
    expect(result.current.role).toBe('company');
    act(() => result.current.applyToJob('designer'));
    expect(result.current.applications['designer']).toBe('applied');
    act(() => result.current.companyUpdateCandidate(SELF_ID, 'designer', 'nominated'));
    let error: string | null = 'x';
    act(() => { error = result.current.companySchedule(SELF_ID, 'designer', '2026-12-02T10:00:00+03:00'); });
    expect(error).toBeNull();
    expect(result.current.applications['designer']).toBe('scheduled');
    expect(result.current.schedules['designer']).toBe('2026-12-02T10:00:00+03:00');
    act(() => result.current.updateApplication('designer', 'completed'));
    act(() => result.current.companyUpdateCandidate(SELF_ID, 'designer', 'accepted'));
    act(() => result.current.switchRole('candidate'));
    act(() => result.current.acceptOffer('designer'));
    expect(result.current.applications['designer']).toBe('hired');
  });
  it('updates pool candidates only along allowed steps and adds jobs', () => {
    const { result } = renderHook(() => useSanad(), { wrapper });
    act(() => result.current.companyUpdateCandidate('c5', 'support', 'accepted'));
    expect(result.current.poolApplications['c5']?.['support']).toBe('accepted');
    act(() => result.current.companyUpdateCandidate('c4', 'analyst', 'rejected'));
    expect(result.current.poolApplications['c4']?.['analyst']).toBe('hired');
    let error: string | null = null;
    act(() => { error = result.current.addCompanyJob('مدخل بيانات', [' '], 1); });
    expect(error).toBe('أضف مهارة مطلوبة واحدة على الأقل.');
    act(() => { result.current.addCompanyJob('مدخل بيانات', ['Excel', 'Excel'], 2); });
    expect(result.current.companyJobs[0]).toMatchObject({ title: 'مدخل بيانات', skills: ['Excel'], minYears: 2, custom: true });
  });
});
