import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { microphoneErrorMessage, SPEECH_LANGUAGE, speechServerMessages, useArabicSpeech } from '@/hooks/use-arabic-speech';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

class FakeRecorder {
  static isTypeSupported = () => true;
  state: 'inactive' | 'recording' = 'inactive';
  mimeType = 'audio/webm;codecs=opus';
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(public stream: MediaStream) {}
  start() { this.state = 'recording'; }
  stop() { this.state = 'inactive'; this.onstop?.(); }
}

describe('Arabic microphone speech-to-text', () => {
  it('is Arabic only', () => {
    expect(SPEECH_LANGUAGE).toBe('ar');
    expect(Object.values(speechServerMessages).every(message => /[؀-ۿ]/.test(message))).toBe(true);
  });

  it('asks for the microphone only after an explicit action, audio only, and releases it on exit', async () => {
    const stop = vi.fn();
    const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    vi.stubGlobal('MediaRecorder', FakeRecorder);
    vi.stubGlobal('WebSocket', class { close() {} send() {} });
    const { result, unmount } = renderHook(() => useArabicSpeech({ mode: 'ai', onTranscript: () => {} }));
    expect(getUserMedia).not.toHaveBeenCalled();
    await act(async () => result.current.toggle());
    expect(getUserMedia).toHaveBeenCalledOnce();
    expect(getUserMedia.mock.lastCall?.[0]).toMatchObject({ video: false, audio: { channelCount: 1 } });
    expect(result.current.status).toBe('recording');
    unmount();
    expect(stop).toHaveBeenCalledOnce();
  });

  it('explains a denied microphone in Arabic and stays idle', async () => {
    const getUserMedia = vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError'));
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    vi.stubGlobal('MediaRecorder', FakeRecorder);
    const { result, unmount } = renderHook(() => useArabicSpeech({ mode: 'ai', onTranscript: () => {} }));
    await act(async () => result.current.toggle());
    expect(result.current.status).toBe('idle');
    expect(result.current.error).toBe(microphoneErrorMessage(new DOMException('Denied', 'NotAllowedError')));
    expect(result.current.error).toContain('الميكروفون');
    unmount();
  });

  it('gives Arabic messages for missing, busy and unsupported microphones', async () => {
    expect(microphoneErrorMessage(new DOMException('x', 'NotFoundError'))).toContain('لم يتم العثور على ميكروفون');
    expect(microphoneErrorMessage(new DOMException('x', 'NotReadableError'))).toContain('مشغول');
    vi.stubGlobal('navigator', {});
    const { result, unmount } = renderHook(() => useArabicSpeech({ mode: 'ai', onTranscript: () => {} }));
    await act(async () => result.current.toggle());
    expect(result.current.error).toContain('الميكروفون غير متاح');
    unmount();
  });
});
