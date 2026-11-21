/** Spoken guidance for blind candidates. Uses the browser's speech synthesis; silent when unavailable. */
export function canSpeak(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function';
}

/**
 * An installed Arabic voice, preferring Saudi and local (offline) voices.
 * Setting only `lang` is not enough: Edge then picks an online voice that fails to start ("interrupted"),
 * and some setups fall back to an English voice that skips Arabic text, so nothing is heard.
 */
function arabicVoice(): SpeechSynthesisVoice | null {
  const voices = typeof window.speechSynthesis.getVoices === 'function' ? window.speechSynthesis.getVoices() : [];
  const arabic = voices.filter(voice => voice.lang.toLowerCase().replace('_', '-').startsWith('ar'));
  return arabic.find(v => v.lang === 'ar-SA' && v.localService) ?? arabic.find(v => v.localService)
    ?? arabic.find(v => v.lang === 'ar-SA') ?? arabic[0] ?? null;
}

// Browsers load the voice list asynchronously: ask for it early so it is ready at the first click.
if (canSpeak() && typeof window.speechSynthesis.getVoices === 'function') {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.addEventListener?.('voiceschanged', () => window.speechSynthesis.getVoices());
}

function utterance(text: string): SpeechSynthesisUtterance {
  const item = new window.SpeechSynthesisUtterance(text);
  item.lang = 'ar-SA';
  item.rate = 0.95;
  const voice = arabicVoice();
  if (voice) { item.voice = voice; item.lang = voice.lang; }
  return item;
}

/** Stop what is being read, then read `parts` in order. */
function say(parts: string[]): boolean {
  const queue = parts.map(part => part.trim()).filter(Boolean);
  if (!canSpeak() || !queue.length) return false;
  const synth = window.speechSynthesis;
  const start = () => queue.forEach(part => synth.speak(utterance(part)));
  if (synth.speaking || synth.pending) {
    synth.cancel();
    window.setTimeout(start, 80);   // speaking right after cancel() is dropped by some browsers
  } else {
    start();
  }
  return true;
}

export function speak(text: string): boolean {
  return say([text]);
}

export function stopSpeaking(): void {
  if (canSpeak()) window.speechSynthesis.cancel();
}

/** Read several short parts in order (long single utterances are cut off by some browser voices). */
export function speakAll(parts: string[]): boolean {
  return say(parts);
}

let describing: AbortController | null = null;

/**
 * Web accessibility assistant: explains the current page aloud in Arabic (AI description from the
 * Sanad API, grounded in the page). If the API cannot be reached it says so, then reads `fallback`.
 */
export async function readPageAloud(fallback: string): Promise<void> {
  describing?.abort();
  const controller = new AbortController();
  describing = controller;
  speak('لحظة، أجهّز وصف الصفحة.');
  const timeout = window.setTimeout(() => controller.abort(), 45000);
  try {
    const { describeCurrentPage } = await import('@/lib/page-reader');
    const reply = await describeCurrentPage(controller.signal);
    if (describing === controller) speakAll(reply.speech);
  } catch {
    if (describing === controller) speakAll(['تعذّر الوصول إلى مساعد وصف الصفحة الآن، تأكد من تشغيل خادم سند.', fallback]);
  } finally {
    window.clearTimeout(timeout);
    if (describing === controller) describing = null;
  }
}
