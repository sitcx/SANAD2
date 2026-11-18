import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { useLocalMedia } from '@/hooks/use-local-media';

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
describe('Local media privacy', () => {
  it('requests camera only after an explicit action and stops tracks on exit', async () => {
    const stop = vi.fn();
    const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    const { result, unmount } = renderHook(() => useLocalMedia());
    expect(getUserMedia).not.toHaveBeenCalled();
    await act(async () => result.current.toggleCamera());
    expect(getUserMedia).toHaveBeenCalledWith({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    expect(result.current.camera).toBe(true);
    unmount();
    expect(stop).toHaveBeenCalledOnce();
    vi.unstubAllGlobals();
  });
  it('never asks for microphone access', async () => {
    const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] });
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    const { result, unmount } = renderHook(() => useLocalMedia());
    await act(async () => result.current.toggleCamera());
    expect(getUserMedia).toHaveBeenCalledTimes(1);
    expect(getUserMedia.mock.lastCall?.[0]).toMatchObject({ audio: false });
    expect('microphone' in result.current).toBe(false);
    expect('toggleMicrophone' in result.current).toBe(false);
    expect('enableDevices' in result.current).toBe(false);
    unmount();
    vi.unstubAllGlobals();
  });
  it('releases the camera when it is switched off again', async () => {
    const stop = vi.fn();
    const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    const { result, unmount } = renderHook(() => useLocalMedia());
    await act(async () => result.current.toggleCamera());
    await act(async () => result.current.toggleCamera());
    expect(result.current.camera).toBe(false);
    expect(stop).toHaveBeenCalledOnce();
    unmount();
  });
  it('keeps camera off when permission is denied', async () => {
    const getUserMedia = vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError'));
    vi.stubGlobal('navigator', { mediaDevices: { getUserMedia } });
    const { result, unmount } = renderHook(() => useLocalMedia());
    await act(async () => result.current.toggleCamera());
    expect(result.current.camera).toBe(false);
    expect(result.current.error.length).toBeGreaterThan(0);
    unmount();
    vi.unstubAllGlobals();
  });
});
