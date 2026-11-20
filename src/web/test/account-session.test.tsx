import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

describe('Named prototype account', () => {
  it('uses the supplied name, not the email prefix, as the shared identity', () => {
    const { result } = renderHook(useSanad, { wrapper: SanadProvider });
    act(() => result.current.signIn('  ريناد  ', 'different-name@example.com'));
    expect(result.current.candidateName).toBe('ريناد');
    expect(result.current.candidateEmail).toBe('different-name@example.com');
    expect(result.current.signedIn).toBe(true);
  });
  it('shares saved profile changes across the current session', () => {
    const { result } = renderHook(() => ({ editor: useSanad(), reader: useSanad() }), { wrapper: SanadProvider });
    act(() => result.current.editor.signIn('ريناد', 'first@example.com'));
    act(() => result.current.editor.updateProfile('نورة', 'updated@example.com'));
    expect(result.current.reader.candidateName).toBe('نورة');
    expect(result.current.reader.candidateEmail).toBe('updated@example.com');
  });
  it('does not update a profile while signed out', () => {
    const { result } = renderHook(useSanad, { wrapper: SanadProvider });
    act(() => result.current.updateProfile('ريناد', 'first@example.com'));
    expect(result.current.candidateName).toBe('أحمد');
    expect(result.current.candidateEmail).toBe('');
  });
  it('clears identity and profile email on sign-out', () => {
    const { result } = renderHook(useSanad, { wrapper: SanadProvider });
    act(() => result.current.signIn('ريناد', 'first@example.com'));
    act(() => result.current.signOut());
    expect(result.current.signedIn).toBe(false);
    expect(result.current.candidateEmail).toBe('');
    expect(result.current.candidateName).toBe('أحمد');
  });
});