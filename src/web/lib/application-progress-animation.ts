import type { getApplicationProgress } from './application-progress';

export type ApplicationProgressSteps = ReturnType<typeof getApplicationProgress>;
export type JourneyStep = {
  node: 'hidden' | 'visible' | 'checked' | 'active' | 'muted';
  connector: 'hidden' | 'drawing' | 'filled' | 'muted';
};
export type JourneyFrame = { delay: number; steps: JourneyStep[] };

export const journeyTiming = { reveal: 500, check: 300, connector: 800, future: 400 } as const;

export function getSettledJourney(progress: ApplicationProgressSteps): JourneyStep[] {
  return progress.map((step, index) => ({
    node: step.state === 'completed' ? 'checked' : step.state === 'current' ? 'active' : 'muted',
    connector: index === progress.length - 1 ? 'hidden' : step.state === 'completed' ? 'filled' : 'muted',
  }));
}

/** Timed presentation of recorded states only; this never changes an application. */
export function getApplicationJourney(progress: ApplicationProgressSteps, previous: ApplicationProgressSteps = []): JourneyFrame[] {
  const current = progress.findIndex(step => step.state === 'current');
  if (current < 0) return [{ delay: 0, steps: getSettledJourney(progress) }];
  const previousCurrent = previous.findIndex(step => step.state === 'current');
  const canContinue = previousCurrent >= 0 && previousCurrent < current && previous.every((step, index) => {
    if (index > previousCurrent) return true;
    const next = progress[index];
    return next?.status === step.status && (index === previousCurrent ? next.state === 'completed' : next.state === step.state);
  });
  const start = canContinue ? previousCurrent : 0;
  const previousSettled = getSettledJourney(previous);
  const steps: JourneyStep[] = progress.map((_, index) => canContinue && index < start
    ? { ...(previousSettled[index] ?? { node: 'hidden', connector: 'hidden' }) }
    : { node: 'hidden', connector: 'hidden' });
  if (canContinue) steps[start] = { node: 'visible', connector: 'hidden' };
  const frames: JourneyFrame[] = [];
  const capture = (delay: number) => frames.push({ delay, steps: steps.map(step => ({ ...step })) });
  capture(0);
  let delay = 160;
  for (let index = start; index <= current; index += 1) {
    const step = progress[index];
    const frameStep = steps[index];
    if (!step || !frameStep) continue;
    frameStep.node = step.state === 'skipped' ? 'muted' : 'visible';
    capture(delay);
    delay += journeyTiming.reveal;
    if (step.state === 'current') {
      frameStep.node = 'active';
      capture(delay);
      delay += journeyTiming.future;
      const final = getSettledJourney(progress);
      return [...frames, { delay, steps: final }];
    }
    if (step.state === 'completed') {
      frameStep.node = 'checked';
      capture(delay);
      delay += journeyTiming.check;
    }
    frameStep.connector = 'drawing';
    capture(delay);
    delay += journeyTiming.connector;
    frameStep.connector = step.state === 'completed' ? 'filled' : 'muted';
  }
  return frames;
}