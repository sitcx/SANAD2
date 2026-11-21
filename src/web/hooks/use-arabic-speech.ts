import { useEffect, useRef, useState } from 'react';

/** The only caption language. The server accepts a sentence only when the spoken language is Arabic. */
export const SPEECH_LANGUAGE = 'ar' as const;
export const STREAM_SAMPLE_RATE = 16000;
const FRAME_SAMPLES = 1600;                  // 100 ms per WebSocket frame
const MAX_BUFFERED_BYTES = 256 * 1024;       // drop audio instead of building up delay on a slow link
const RECONNECT_DELAYS_MS = [1000, 2000, 4000, 8000, 15000];

export type LiveCaptionStatus = 'connecting' | 'listening' | 'muted' | 'error' | 'unsupported';
export type InterviewAgentMode = 'ai' | 'human';

export function microphoneErrorMessage(error: unknown): string {
  const name = error instanceof Error ? error.name : '';
  if (name === 'NotAllowedError' || name === 'SecurityError') return 'لم يُسمح بالوصول إلى الميكروفون، فلا تعمل الترجمة المباشرة. اسمح للمتصفح باستخدام الميكروفون من شريط العنوان ثم أعد تحميل الصفحة.';
  if (name === 'NotFoundError' || name === 'OverconstrainedError') return 'لم يتم العثور على ميكروفون متصل. صِل ميكروفونًا ثم أعد تحميل الصفحة.';
  if (name === 'NotReadableError' || name === 'AbortError') return 'الميكروفون مشغول في تطبيق آخر أو تعذّر تشغيله. أغلق التطبيق الآخر ثم أعد تحميل الصفحة.';
  return 'تعذّر تشغيل الميكروفون. تحقق من الجهاز وأذونات المتصفح ثم أعد تحميل الصفحة.';
}

/** Arabic messages for the server's speech error codes (the server also sends its own Arabic text). */
export const speechServerMessages = {
  non_arabic_speech: 'تتعرّف الترجمة المباشرة على الكلام العربي فقط. أعد الجملة باللغة العربية.',
  speech_not_configured: 'الترجمة المباشرة غير مفعّلة على الخادم: مفتاح OpenRouter غير موجود.',
  speech_service_unavailable: 'خدمة الترجمة المباشرة غير متاحة حاليًا. تحقق من اتصال الخادم بالإنترنت.',
  invalid_audio: 'تعذّرت قراءة الصوت. تحقق من الميكروفون.',
} as const satisfies Record<string, string>;
const CONNECTION_LOST = 'انقطع الاتصال بخدمة الترجمة المباشرة. جارٍ إعادة الاتصال…';
const CONNECTION_FAILED = 'تعذّر الاتصال بخدمة الترجمة المباشرة. تأكد من تشغيل خادم سند ثم أعد تحميل الصفحة.';
const UNSUPPORTED = 'هذا المتصفح لا يدعم الترجمة المباشرة. استخدم إصدارًا حديثًا من Chrome أو Edge أو Firefox عبر localhost أو https.';

function apiBase(): string {
  const url = (import.meta.env['VITE_SANAD_API_URL'] as string | undefined) || 'http://localhost:8010';
  return url.replace(/\/+$/, '').replace(/^http/, 'ws');
}

function newSessionId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : `s-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/** Turns microphone blocks at the device rate into 100 ms frames of 16 kHz mono 16-bit PCM. */
export class Pcm16Downsampler {
  private position = 0;
  private sum = 0;
  private count = 0;
  private frame = new Int16Array(FRAME_SAMPLES);
  private filled = 0;
  constructor(private readonly inputRate: number, private readonly onFrame: (frame: ArrayBuffer) => void) {}
  push(input: Float32Array) {
    const step = this.inputRate / STREAM_SAMPLE_RATE;
    for (let i = 0; i < input.length; i++) {
      this.sum += input[i] ?? 0; this.count++; this.position++;
      if (this.position >= step) {
        this.position -= step;
        const value = Math.max(-1, Math.min(1, this.sum / this.count));
        this.frame[this.filled++] = value < 0 ? value * 0x8000 : value * 0x7fff;
        this.sum = 0; this.count = 0;
        if (this.filled === FRAME_SAMPLES) { this.onFrame(this.frame.slice().buffer); this.filled = 0; }
      }
    }
  }
}

const WORKLET = `class SanadMicTap extends AudioWorkletProcessor {
  process(inputs) { const channel = inputs[0] && inputs[0][0]; if (channel) this.port.postMessage(channel.slice(0)); return true; }
}
registerProcessor('sanad-mic-tap', SanadMicTap);`;

type ServerReply = { type: string; utterance?: number; text?: string; final?: boolean; last_question?: string | null; error?: string; details?: string[] };

/**
 * Live Arabic captions for the interview room.
 * Starts when the room opens (the browser asks for microphone permission once), streams the microphone
 * continuously to the Sanad server (WS /interview/{session}, binary 16 kHz PCM), shows the sentence in
 * progress as it is spoken, and reports each finished sentence after the Interview Agent received it.
 * Audio is not recorded or stored in the browser; every track stops when the room closes.
 */
export function useLiveArabicCaptions({ mode, onQuestion }: { mode: InterviewAgentMode; onQuestion: (text: string) => void }) {
  const [status, setStatus] = useState<LiveCaptionStatus>('connecting');
  const [partial, setPartial] = useState('');
  const [error, setError] = useState('');
  const [needsGesture, setNeedsGesture] = useState(false);
  const latest = useRef({ mode, onQuestion });
  latest.current = { mode, onQuestion };
  const muted = useRef(false);
  const socket = useRef<WebSocket | null>(null);
  const started = useRef(false);
  const track = useRef<MediaStreamTrack | null>(null);
  const context = useRef<AudioContext | null>(null);

  useEffect(() => {
    let disposed = false;
    let stream: MediaStream | null = null;
    let reconnectTimer = 0;
    let attempts = 0;
    const sessionId = newSessionId();
    const cleanups: Array<() => void> = [];

    function sendFrame(frame: ArrayBuffer) {
      const ws = socket.current;
      if (muted.current || !started.current || !ws || ws.readyState !== WebSocket.OPEN || ws.bufferedAmount > MAX_BUFFERED_BYTES) return;
      ws.send(frame);
    }

    function connect() {
      if (disposed) return;
      started.current = false;
      const ws = new WebSocket(`${apiBase()}/interview/${sessionId}`);
      ws.binaryType = 'arraybuffer';
      socket.current = ws;
      ws.onopen = () => ws.send(JSON.stringify({ type: 'start', mode: latest.current.mode }));
      ws.onmessage = event => {
        if (typeof event.data !== 'string') return;
        let reply: ServerReply;
        try { reply = JSON.parse(event.data) as ServerReply; } catch { return; }
        if (reply.type === 'started') { started.current = true; attempts = 0; setError(''); setStatus(muted.current ? 'muted' : 'listening'); return; }
        if (reply.type === 'caption') {   // a final caption stays on screen until the agent's state arrives
          setError('');
          setPartial(reply.text ?? '');
          return;
        }
        if (reply.type === 'state') { const text = (reply.last_question ?? '').trim(); if (text) latest.current.onQuestion(text); setPartial(''); return; }
        if (reply.type === 'error') {
          setPartial('');
          setError(reply.details?.[0] || (speechServerMessages as Record<string, string | undefined>)[reply.error ?? ''] || 'تعذّرت ترجمة الجملة الأخيرة. تابع الحديث بالعربية.');
        }
      };
      ws.onclose = () => {
        if (socket.current === ws) socket.current = null;
        started.current = false;
        if (disposed) return;
        setPartial('');
        if (attempts >= RECONNECT_DELAYS_MS.length) { setStatus('error'); setError(CONNECTION_FAILED); return; }
        setStatus('connecting'); setError(CONNECTION_LOST);
        reconnectTimer = window.setTimeout(connect, RECONNECT_DELAYS_MS[attempts++]);
      };
    }

    async function startMicrophone() {
      if (!navigator.mediaDevices?.getUserMedia || typeof AudioContext === 'undefined' || typeof WebSocket === 'undefined') {
        setStatus('unsupported'); setError(UNSUPPORTED); return;
      }
      // Created right away so it starts inside the "join" click; resumed on the next tap if the browser waits.
      let ctx: AudioContext;   // 16 kHz context: the browser's own high-quality resampler (fallback: device rate + Pcm16Downsampler)
      try { ctx = new AudioContext({ sampleRate: STREAM_SAMPLE_RATE }); } catch { ctx = new AudioContext(); }
      context.current = ctx;
      cleanups.push(() => { void ctx.close().catch(() => {}); });
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true }, video: false });
      } catch (err) {
        if (!disposed) { setStatus('error'); setError(microphoneErrorMessage(err)); }
        return;
      }
      if (disposed) { stream.getTracks().forEach(t => t.stop()); return; }
      track.current = stream.getAudioTracks()[0] ?? null;
      if (track.current) { track.current.enabled = !muted.current; track.current.onended = () => { if (!disposed) { setStatus('error'); setError('توقف الميكروفون. تحقق من الجهاز ثم أعد تحميل الصفحة.'); } }; }
      const source = ctx.createMediaStreamSource(stream);
      const silent = ctx.createGain(); silent.gain.value = 0; silent.connect(ctx.destination);   // keeps the graph running, plays nothing
      const downsampler = new Pcm16Downsampler(ctx.sampleRate, sendFrame);
      try {
        const url = URL.createObjectURL(new Blob([WORKLET], { type: 'application/javascript' }));
        await ctx.audioWorklet.addModule(url); URL.revokeObjectURL(url);
        const tap = new AudioWorkletNode(ctx, 'sanad-mic-tap');
        tap.port.onmessage = event => downsampler.push(event.data as Float32Array);
        source.connect(tap); tap.connect(silent);
      } catch {
        const processor = ctx.createScriptProcessor(4096, 1, 1);   // older browsers without AudioWorklet
        processor.onaudioprocess = event => downsampler.push(event.inputBuffer.getChannelData(0));
        source.connect(processor); processor.connect(silent);
      }
      if (ctx.state === 'suspended') {
        setNeedsGesture(true);
        const resume = () => { void ctx.resume().then(() => { if (!disposed) setNeedsGesture(false); }); };
        window.addEventListener('pointerdown', resume, { once: true });
        window.addEventListener('keydown', resume, { once: true });
        cleanups.push(() => { window.removeEventListener('pointerdown', resume); window.removeEventListener('keydown', resume); });
      }
      connect();
    }

    void startMicrophone();
    return () => {
      disposed = true;
      window.clearTimeout(reconnectTimer);
      stream?.getTracks().forEach(t => t.stop());
      track.current = null;
      socket.current?.close(); socket.current = null;
      cleanups.forEach(fn => fn());
      context.current = null;
    };
  }, []);

  function toggleMute() {
    if (status === 'error' || status === 'unsupported') return;
    muted.current = !muted.current;
    if (track.current) track.current.enabled = !muted.current;
    if (muted.current) {
      setPartial('');
      const ws = socket.current;
      if (ws?.readyState === WebSocket.OPEN && started.current) ws.send(JSON.stringify({ type: 'audio_end' }));   // finish the sentence in progress
    }
    setStatus(muted.current ? 'muted' : started.current ? 'listening' : 'connecting');
  }

  return { status, partial, error, needsGesture, language: SPEECH_LANGUAGE, toggleMute };
}

export type LiveArabicCaptions = ReturnType<typeof useLiveArabicCaptions>;
