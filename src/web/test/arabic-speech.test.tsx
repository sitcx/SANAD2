import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { microphoneErrorMessage, Pcm16Downsampler, SPEECH_LANGUAGE, speechServerMessages, useLiveArabicCaptions } from '@/hooks/use-arabic-speech';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('Live Arabic captions', () => {
  it('is Arabic only, with Arabic server messages', () => {
    expect(SPEECH_LANGUAGE).toBe('ar');
    expect(Object.values(speechServerMessages).every(message => /[؀-ۿ]/.test(message))).toBe(true);
  });

  it('turns 48 kHz microphone audio into 100 ms frames of 16 kHz PCM16', () => {
    const frames: ArrayBuffer[] = [];
    const downsampler = new Pcm16Downsampler(48000, frame => frames.push(frame));
    downsampler.push(new Float32Array(48000).fill(0.5));   // 1 s
    expect(frames).toHaveLength(10);
    const first = new Int16Array(frames[0]!);
    expect(first).toHaveLength(1600);
    expect(first.every(v => Math.abs(v - 16383) <= 1)).toBe(true);
  });

  it('asks for the microphone as soon as the room opens, audio only', async () => {
    const getUserMedia = vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError'));
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    vi.stubGlobal('AudioContext', class { state = 'running'; sampleRate = 48000; close() { return Promise.resolve(); } });
    const { result, unmount } = renderHook(() => useLiveArabicCaptions({ mode: 'ai', onQuestion: () => {} }));
    await waitFor(() => expect(getUserMedia).toHaveBeenCalledOnce());
    expect(getUserMedia.mock.lastCall?.[0]).toMatchObject({ video: false, audio: { channelCount: 1 } });
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.error).toBe(microphoneErrorMessage(new DOMException('Denied', 'NotAllowedError')));
    unmount();
  });

  it('explains missing, busy and unsupported microphones in Arabic', async () => {
    expect(microphoneErrorMessage(new DOMException('x', 'NotFoundError'))).toContain('لم يتم العثور على ميكروفون');
    expect(microphoneErrorMessage(new DOMException('x', 'NotReadableError'))).toContain('مشغول');
    vi.stubGlobal('navigator', {});
    const { result, unmount } = renderHook(() => useLiveArabicCaptions({ mode: 'ai', onQuestion: () => {} }));
    await waitFor(() => expect(result.current.status).toBe('unsupported'));
    expect(result.current.error).toContain('لا يدعم الترجمة المباشرة');
    act(() => result.current.toggleMute());   // no effect without a microphone
    expect(result.current.status).toBe('unsupported');
    unmount();
  });
});
