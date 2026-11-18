import { useEffect, useRef, useState } from 'react';

export function mediaErrorMessage(error: unknown): string {
  const name = error instanceof Error ? error.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'لم يُسمح بالوصول للكاميرا. اسمح بالكاميرا من إعدادات المتصفح ثم حاول مجددًا.';
  if (name === 'NotFoundError') return 'لم يتم العثور على كاميرا متصلة. تحقق من الكاميرا ثم حاول مجددًا.';
  if (name === 'NotReadableError') return 'الكاميرا مشغولة في تطبيق آخر. أغلق التطبيق ثم حاول مجددًا.';
  return 'تعذّر تشغيل الكاميرا. تحقق من الاتصال وأذونات المتصفح ثم حاول مجددًا.';
}

/** Local camera preview only: no audio, recording, upload, peer connection, or persistence. */
export function useLocalMedia() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const cameraStream = useRef<MediaStream | null>(null);
  const mounted = useRef(false);
  const [camera, setCamera] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; cameraStream.current?.getTracks().forEach(track => track.stop()); };
  }, []);
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const stream = camera ? cameraStream.current : null;
    if (video.srcObject === stream) return;
    video.srcObject = stream;
    if (stream) void video.play().catch(error => { if (mounted.current && error instanceof Error && error.name !== 'AbortError') setError('تعذّر عرض الكاميرا. أوقفها ثم شغّلها مجددًا.'); });
  });
  async function toggleCamera() {
    if (busy) return;
    if (cameraStream.current) { cameraStream.current.getTracks().forEach(track => track.stop()); cameraStream.current = null; setCamera(false); return; }
    setError('');
    if (!navigator.mediaDevices?.getUserMedia) { setError('الكاميرا غير متاحة هنا. افتح الموقع في متصفح حديث عبر اتصال آمن.'); return; }
    setBusy(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
      if (!mounted.current) { stream.getTracks().forEach(track => track.stop()); return; }
      cameraStream.current = stream;
      stream.getTracks().forEach(track => { track.onended = () => { cameraStream.current = null; if (mounted.current) setCamera(false); }; });
      setCamera(true);
    } catch (error) { if (mounted.current) setError(mediaErrorMessage(error)); }
    finally { if (mounted.current) setBusy(false); }
  }
  return { videoRef, camera, busy, error, toggleCamera: () => void toggleCamera() };
}

export type LocalMedia = ReturnType<typeof useLocalMedia>;
