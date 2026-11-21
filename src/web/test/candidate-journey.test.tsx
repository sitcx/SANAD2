import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { careerQuestions, careerTracks, rankCareerTracks } from '@/lib/career-discovery';
import { SanadProvider, useSanad } from '@/lib/sanad-context';
import { canUpdateApplication, statusLabels } from '@/lib/sanad-data';
import { acceptSentence, confirmHuman, pressOther, signSentenceOptions, startInterpreter } from '@/lib/sign-interpreter';
import { advanceTicket, categoriesFor, createTicket, rateTicket } from '@/lib/support-tickets';

const wrapper = ({ children }: { children: ReactNode }) => <SanadProvider>{children}</SanadProvider>;

describe('interpreter rules', () => {
  it('switches to human on the third miss and never back', () => {
    let session = startInterpreter('ai');
    session = pressOther(pressOther(session));
    expect(session.mode).toBe('ai');
    session = pressOther(session);
    expect(session).toMatchObject({ mode: 'human', reason: 'auto' });
    expect(pressOther(session)).toBe(session);
  });
  it('resets the miss counter after an accepted sentence', () => {
    const session = acceptSentence(pressOther(pressOther(startInterpreter('ai'))));
    expect(session.otherCount).toBe(0);
    expect(pressOther(session).mode).toBe('ai');
  });
  it('marks a confirmed request as manual', () => {
    expect(confirmHuman(startInterpreter('ai'))).toMatchObject({ mode: 'human', reason: 'manual' });
  });
  it('offers three distinct sentences including the answer, different each round', () => {
    const first = signSentenceOptions('إجابتي', 0);
    const second = signSentenceOptions('إجابتي', 1);
    expect(first).toHaveLength(3);
    expect(new Set(first).size).toBe(3);
    expect(first).toContain('إجابتي');
    expect(second).not.toEqual(first);
  });
});

describe('career discovery', () => {
  it('has a question per step with one option per track', () => {
    for (const question of careerQuestions) expect(question.options.map(option => option.track).sort()).toEqual(careerTracks.map(track => track.id).sort());
  });
  it('ranks the most chosen track first', () => {
    const ranked = rankCareerTracks(['creative', 'creative', 'tech', 'creative', 'service']);
    expect(ranked[0]).toMatchObject({ track: { id: 'creative' }, percent: 60 });
  });
});

describe('hired status and support tickets', () => {
  it('moves accepted to hired only', () => {
    expect(statusLabels.hired).toBe('موظف');
    expect(canUpdateApplication('accepted', 'hired')).toBe(true);
    expect(canUpdateApplication('completed', 'hired')).toBe(false);
  });
  it('shows request types by communication mode', () => {
    expect(categoriesFor('sign').map(item => item.id)).toEqual(['interpreter', 'captions', 'general']);
    expect(categoriesFor('voice').map(item => item.id)).toEqual(['accessible-document', 'screen-reader', 'general']);
  });
  it('goes received → in progress → resolved, then accepts one rating', () => {
    const ticket = createTicket('t1', 'analyst', 'interpreter', ' اجتماع الأحد ', '2026-11-21T09:00:00Z')!;
    expect(ticket.details).toBe('اجتماع الأحد');
    expect(rateTicket(ticket, 5).rating).toBeNull();
    const resolved = advanceTicket(advanceTicket(ticket, 'a'), 'b');
    expect(resolved.status).toBe('resolved');
    expect(advanceTicket(resolved, 'c')).toBe(resolved);
    const rated = rateTicket(resolved, 4);
    expect(rated.rating).toBe(4);
    expect(rateTicket(rated, 1).rating).toBe(4);
    expect(createTicket('t2', 'analyst', 'general', '   ', 'x')).toBeNull();
  });

  it('runs the candidate session from signup to a resolved support request', () => {
    vi.useFakeTimers();
    const { result } = renderHook(() => useSanad(), { wrapper });
    act(() => result.current.signIn('سارة', 'sara@example.com', 'voice'));
    expect(result.current.communicationMode).toBe('voice');
    act(() => result.current.completeCareerDiscovery('tech'));
    expect(result.current).toMatchObject({ careerTrack: 'tech', careerDecided: true });
    expect(result.current.submitSupportTicket('general', 'قبل التوظيف')).toBe(false);
    act(() => result.current.updateApplication('analyst', 'completed'));
    act(() => result.current.updateApplication('analyst', 'accepted'));
    act(() => result.current.acceptOffer('analyst'));
    expect(result.current.applications['analyst']).toBe('hired');
    act(() => { result.current.submitSupportTicket('screen-reader', 'قارئ الشاشة لا يقرأ نظام الحضور'); });
    expect(result.current.supportTickets[0]?.status).toBe('received');
    act(() => { vi.advanceTimersByTime(4100); });
    expect(result.current.supportTickets[0]?.status).toBe('in_progress');
    act(() => { vi.advanceTimersByTime(4100); });
    expect(result.current.supportTickets[0]?.status).toBe('resolved');
    vi.useRealTimers();
  });
});
