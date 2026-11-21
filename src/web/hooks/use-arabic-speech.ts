import { useEffect, useRef, useState } from 'react';

/** The only transcription language. The server (Whisper Large-v3) is fixed to Arabic as well. */
export const SPEECH_LANGUAGE = 'ar' as const;
/** Recordings stop automatically before the server limit (config.yaml speech.max_seconds = 120). */
export const MAX_RECORDING_SECONDS = 115;
const REPLY_TIMEOUT_MS = 5 * 60 * 1000;   // the first question may wait for the model to load
const AUDIO_TYPES = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/webm', 'audio/mp4'];

export type ArabicSpeechStatus = 'idle' | 'requesting' | 'recording' | 'transcribing';
export type InterviewAgentMode = 'ai' | 'human';

export function microphoneErrorMessage(error: unknown): string {
  const name = error instanceof Error ? error.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'لم يُسمح بالوصول إلى الميكروفون. اسمح للمتصفح باستخدام الميكروفون ثم حاول مجددًا.';
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'لم يتم العثور على ميكروفون متصل. صِل ميكروفونًا ثم حاول مجددًا.';
  if (name === 'NotReadableError' || name === 'AbortError') return 'الميكروفون مشغول في تطبيق آخر أو تعذّر تشغيله. أغلق التطبيق ثم حاول مجددًا.';
  return 'تعذّر تشغيل الميكروفون. تحقق من الجهاز وأذونات المتصفح ثم حاول مجددًا.';
}

/** Arabic messages for the server's speech error codes (the server also sends its own Arabic text). */
export const speechServerMessages = {
  no_speech: 'لم يُلتقط كلام واضح. اقترب من الميكروفون وتحدّث بالعربية ثم حاول مجددًا.',
  non_arabic_speech: 'يتعرّف سند على الكلام العربي فقط. أعد السؤال باللغة العربية.',
  invalid_audio: 'تعذّرت قراءة التسجيل الصوتي. سجّل السؤال مرة أخرى.',
  speech_model_unavailable: 'خدمة تحويل الكلام العربي إلى نص غير متاحة على الخادم حاليًا. اكتب السؤال بدلًا من ذلك.',
} as const satisfies Record<string, string>;
const CONNECTION_ERROR = 'تعذّر الاتصال بخدمة تحويل الكلام العربي. تأكد من تشغيل خادم سند ثم حاول مجددًا.';
const TIMEOUT_ERROR = 'استغرق تحويل الكلام وقتًا أطول من المتوقع. حاول مرة أخرى بتسجيل أقصر.';

function apiBase(): string {
  const url = (import.meta.env['VITE_SANAD_API_URL'] as string | undefined) || 'http://localhost:8010';
  return url.replace(/\/+$/, '').replace(/^http/, 'ws');
}

function newSessionId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',', 2)[1] ?? '');
    reader.onerror = () => reject(reader.error ?? new Error('read failed'));
    reader.readAsDataURL(blob);
  });
}

type ServerReply = { type: string; last_question?: string | null; error?: string; details?: string[] };
type Pending = { resolve: (reply: ServerReply) => void; reject: (error: Error) => void };

/**
 * The recruiter's microphone -> Arabic text, through the Interview Agent (WS /interview/{session}).
 * Opt-in: the microphone is requested only when recording starts, and every track stops when
 * recording stops or the room closes. The audio goes to the Sanad server only, where Whisper
 * Large-v3 transcribes it in Arabic only; the agent stores the text as the current question.
 */
export function useArabicSpeech({ mode, onTranscript }: { mode: InterviewAgentMode; onTranscript: (text: string) => void }) {
  const [status, setStatus] = useState<ArabicSpeechStatus>('idle');
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState('');
  const [transcript, setTranscript] = useState('');
  const mounted = useRef(false);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timers = useRef<number[]>([]);
  const socket = useRef<WebSocket | null>(null);
  const ready = useRef<Promise<WebSocket> | null>(null);
  const pending = useRef<Pending | null>(null);
  const sessionId = useRef(newSessionId());
  const latest = useRef({ mode, onTranscript });
  latest.current = { mode, onTranscript };

  function clearTimers() { timers.current.forEach(id => window.clearTimeout(id)); timers.current = []; }
  function releaseMicrophone() { stream.current?.getTracks().forEach(track => track.stop()); stream.current = null; }

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false; clearTimers();
      if (recorder.current && recorder.current.state !== 'inactive') { recorder.current.onstop = null; recorder.current.stop(); }
      releaseMicrophone();
      pending.current?.reject(new Error('closed')); pending.current = null;
      socket.current?.close(); socket.current = null; ready.current = null;
    };
  }, []);

  function connect(): Promise<WebSocket> {
    if (ready.current) return ready.current;
    const attempt = new Promise<WebSocket>((resolve, reject) => {
      let started = false;
      const ws = new WebSocket(`${apiBase()}/interview/${sessionId.current}`);
      socket.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ type: 'start', mode: latest.current.mode }));
      ws.onmessage = event => {
        let reply: ServerReply;
        try { reply = JSON.parse(String(event.data)) as ServerReply; } catch { return; }
        if (!started) { if (reply.type === 'started') { started = true; resolve(ws); } else { reject(new Error(reply.error ?? 'start failed')); ws.close(); } return; }
        const waiting = pending.current; pending.current = null; waiting?.resolve(reply);
      };
      ws.onclose = () => {
        if (socket.current === ws) { socket.current = null; ready.current = null; }
        if (!started) reject(new Error('closed'));
        const waiting = pending.current; pending.current = null; waiting?.reject(new Error('closed'));
      };
    });
    ready.current = attempt;
    attempt.catch(() => { if (ready.current === attempt) ready.current = null; });
    return attempt;
  }

  async function ask(audioB64: string): Promise<ServerReply> {
    const ws = await connect();
    return new Promise<ServerReply>((resolve, reject) => {
      const timer = window.setTimeout(() => { if (pending.current) { pending.current = null; reject(new Error('timeout')); } }, REPLY_TIMEOUT_MS);
      pending.current = { resolve: reply => { window.clearTimeout(timer); resolve(reply); }, reject: err => { window.clearTimeout(timer); reject(err); } };
      ws.send(JSON.stringify({ type: 'question', audio_b64: audioB64 }));
    });
  }

  async function transcribe(blob: Blob) {
    if (!mounted.current) return;
    if (blob.size < 1000) { setStatus('idle'); setError('التسجيل قصير جدًا. اضغط زر الميكروفون، تحدّث بالعربية، ثم أوقف التسجيل.'); return; }
    setStatus('transcribing');
    try {
      const reply = await ask(await blobToBase64(blob));
      if (!mounted.current) return;
      if (reply.type === 'error') { setError(reply.details?.[0] || (speechServerMessages as Record<string, string | undefined>)[reply.error ?? ''] || 'تعذّر تحويل الكلام العربي إلى نص. حاول مرة أخرى.'); return; }
      const text = (reply.last_question ?? '').trim();
      if (!text) { setError(speechServerMessages.no_speech); return; }
      setTranscript(text); latest.current.onTranscript(text);
    } catch (err) {
      if (mounted.current) setError(err instanceof Error && err.message === 'timeout' ? TIMEOUT_ERROR : CONNECTION_ERROR);
    } finally {
      if (mounted.current) setStatus('idle');
    }
  }

  async function start() {
    if (status !== 'idle') return;
    setError('');
    if (!navigator.mediaDevices?.getUserMedia) { setError('الميكروفون غير متاح هنا. افتح الموقع في متصفح حديث عبر اتصال آمن (localhost أو https).'); return; }
    if (typeof MediaRecorder === 'undefined') { setError('هذا المتصفح لا يدعم تسجيل الصوت. استخدم إصدارًا حديثًا من Chrome أو Edge أو Firefox.'); return; }
    setStatus('requesting');
    let media: MediaStream;
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }, video: false });
    } catch (err) { if (mounted.current) { setStatus('idle'); setError(microphoneErrorMessage(err)); } return; }
    if (!mounted.current) { media.getTracks().forEach(track => track.stop()); return; }
    stream.current = media;
    const mimeType = AUDIO_TYPES.find(type => MediaRecorder.isTypeSupported?.(type));
    let rec: MediaRecorder;
    try { rec = new MediaRecorder(media, mimeType ? { mimeType } : undefined); }
    catch { releaseMicrophone(); setStatus('idle'); setError('تعذّر بدء تسجيل الصوت في هذا المتصفح. حاول مجددًا.'); return; }
    chunks.current = [];
    rec.ondataavailable = event => { if (event.data.size > 0) chunks.current.push(event.data); };
    rec.onstop = () => { clearTimers(); releaseMicrophone(); recorder.current = null; void transcribe(new Blob(chunks.current, { type: rec.mimeType || mimeType || 'audio/webm' })); };
    rec.onerror = () => { clearTimers(); releaseMicrophone(); recorder.current = null; if (mounted.current) { setStatus('idle'); setError('توقف تسجيل الميكروفون بشكل غير متوقع. حاول مجددًا.'); } };
    media.getTracks().forEach(track => { track.onended = () => { if (rec.state !== 'inactive') rec.stop(); }; });
    recorder.current = rec;
    rec.start();
    setSeconds(0); setStatus('recording');
    const began = Date.now();
    const tick = () => { if (!recorder.current) return; const elapsed = Math.floor((Date.now() - began) / 1000); setSeconds(elapsed); if (elapsed >= MAX_RECORDING_SECONDS) stop(); else timers.current.push(window.setTimeout(tick, 250)); };
    timers.current.push(window.setTimeout(tick, 250));
    void connect().catch(() => {});   // open the agent session while the recruiter speaks
  }

  function stop() {
    const rec = recorder.current;
    if (rec && rec.state !== 'inactive') rec.stop();
  }

  function toggle() { if (status === 'recording') stop(); else void start(); }

  return { status, seconds, error, transcript, language: SPEECH_LANGUAGE, start: () => void start(), stop, toggle, clearError: () => setError('') };
}

export type ArabicSpeech = ReturnType<typeof useArabicSpeech>;
