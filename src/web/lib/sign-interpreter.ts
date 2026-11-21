/**
 * Interpreter rules for the sign-language interview.
 *
 * 1. The candidate picks AI or human before the interview; the other choice is then disabled.
 * 2. AI mode: the recognised sign is shown as sentence options and the candidate picks one.
 * 3. Pressing "غير ذلك" three times switches to a human interpreter automatically.
 * 4. The candidate can ask for a human at any time, after a confirmation.
 * Once the session is human it never returns to AI.
 */
export type InterpreterChoice = 'ai' | 'human';
export type SwitchReason = 'start' | 'auto' | 'manual';

export const MAX_OTHER_ATTEMPTS = 3;

export const interpreterChoices = [
  { id: 'ai', label: 'مترجم الذكاء الاصطناعي', description: 'يتعرّف على إشارتك ويعرض لك الجمل المحتملة لتختار الصحيحة.' },
  { id: 'human', label: 'مترجم بشري', description: 'مترجم لغة إشارة يترجم بينك وبين مسؤول التوظيف طوال المقابلة.' },
] as const satisfies readonly { id: InterpreterChoice; label: string; description: string }[];

export interface InterpreterSession {
  mode: InterpreterChoice;
  otherCount: number;
  reason: SwitchReason;
}

export function startInterpreter(choice: InterpreterChoice): InterpreterSession {
  return { mode: choice, otherCount: 0, reason: 'start' };
}

/** The candidate rejected every suggested sentence. */
export function pressOther(session: InterpreterSession): InterpreterSession {
  if (session.mode === 'human') return session;
  const otherCount = session.otherCount + 1;
  return otherCount >= MAX_OTHER_ATTEMPTS ? { mode: 'human', otherCount, reason: 'auto' } : { ...session, otherCount };
}

/** The candidate confirmed the request for a human interpreter. */
export function confirmHuman(session: InterpreterSession): InterpreterSession {
  return session.mode === 'human' ? session : { ...session, mode: 'human', reason: 'manual' };
}

/** A sentence was accepted, so the miss counter starts again for the next answer. */
export function acceptSentence(session: InterpreterSession): InterpreterSession {
  return session.mode === 'ai' ? { ...session, otherCount: 0 } : session;
}

const alternatives = [
  'هل يمكنك إعادة السؤال من فضلك؟',
  'أحتاج وقتًا إضافيًا لأفكر في الإجابة.',
  'لدي خبرة في هذا المجال وأرغب في التوضيح أكثر.',
  'لم أفهم السؤال جيدًا، هل يمكن تبسيطه؟',
  'عملت على مشروع مشابه في وظيفتي السابقة.',
  'أفضّل أن أشرح ذلك بمثال من عملي.',
];

/**
 * Simulated recognition result: three candidate sentences for one signed answer.
 * Each new round (after "غير ذلك") shows a different set and order.
 */
export function signSentenceOptions(answer: string, round: number): string[] {
  const start = (round * 2) % alternatives.length;
  const others = [alternatives[start]!, alternatives[(start + 1) % alternatives.length]!];
  if (!answer.trim()) return others;
  const options = [...others];
  options.splice(round % 3, 0, answer.trim());
  return options;
}
