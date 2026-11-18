import { act, fireEvent, render, renderHook, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { JobCommunicationPreferences } from '@/components/job-communication-preferences';
import { getSharedCommunicationNeeds } from '@/lib/communication-needs';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

describe('Job-plan communication requirements', () => {
  it('allows several preferences to remain selected together', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.setJobPreferences('analyst', ['sign', 'text', 'hearing-aid']));
    expect(result.current.preferences['analyst']).toEqual(['sign', 'text', 'hearing-aid']);
  });

  it('rejects extra options and duplicate selections', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.setJobPreferences('analyst', ['sign', 'captions', 'chat', 'interpreter', 'sign']));
    expect(result.current.preferences['analyst']).toEqual(['sign']);
  });

  it('keeps other needs separately for each candidate job', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.setAdditionalCommunicationNeeds('analyst', 'إضاءة واضحة أمام المتحدث'));
    act(() => result.current.setAdditionalCommunicationNeeds('support', 'وقت إضافي لقراءة السؤال'));
    act(() => result.current.selectJob('support'));
    act(() => result.current.selectJob('analyst'));
    expect(result.current.additionalCommunicationNeeds['analyst']).toBe('إضاءة واضحة أمام المتحدث');
    expect(result.current.additionalCommunicationNeeds['support']).toBe('وقت إضافي لقراءة السؤال');
  });

  it('shares selected requirements and entered other needs with the employer', () => {
    const { result } = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => result.current.setJobPreferences('analyst', ['sign', 'other']));
    act(() => result.current.setAdditionalCommunicationNeeds('analyst', 'إضاءة واضحة أمام المتحدث'));
    const shared = getSharedCommunicationNeeds(result.current.preferences['analyst'] ?? [], result.current.additionalCommunicationNeeds['analyst'] ?? '');
    expect(shared.map(item => item.id)).toEqual(['sign', 'other']);
    expect(shared.find(item => item.id === 'other')?.additionalNeeds).toBe('إضاءة واضحة أمام المتحدث');
  });

  it('does not share inactive other needs after deselection', () => {
    expect(getSharedCommunicationNeeds(['text'], 'إضاءة واضحة أمام المتحدث').map(item => item.additionalNeeds)).toEqual(['']);
    expect(getSharedCommunicationNeeds([], 'إضاءة واضحة أمام المتحدث')).toEqual([]);
  });

  it('shows the other-needs editor only while selected and restores the candidate draft on reselection', () => {
    render(<SanadProvider><JobCommunicationPreferences jobId="analyst" /></SanadProvider>);
    const other = screen.getByRole('checkbox', { name: 'احتياج آخر' });
    expect(screen.queryByRole('textbox')).toBeNull();
    fireEvent.click(other);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'إضاءة واضحة أمام المتحدث' } });
    fireEvent.click(other);
    expect(screen.queryByRole('textbox')).toBeNull();
    fireEvent.click(other);
    expect((screen.getByRole('textbox') as HTMLTextAreaElement).value).toBe('إضاءة واضحة أمام المتحدث');
  });

  it('keeps candidate requirements session-only and isolated from new candidate sessions', () => {
    const first = renderHook(() => useSanad(), { wrapper: SanadProvider });
    act(() => first.result.current.setJobPreferences('analyst', ['sign', 'other']));
    act(() => first.result.current.setAdditionalCommunicationNeeds('analyst', 'إضاءة واضحة أمام المتحدث'));
    const second = renderHook(() => useSanad(), { wrapper: SanadProvider });
    expect(second.result.current.preferences).toEqual({});
    expect(second.result.current.additionalCommunicationNeeds).toEqual({});
    first.unmount();
    const fresh = renderHook(() => useSanad(), { wrapper: SanadProvider });
    expect(fresh.result.current.preferences).toEqual({});
    expect(fresh.result.current.additionalCommunicationNeeds).toEqual({});
  });
});