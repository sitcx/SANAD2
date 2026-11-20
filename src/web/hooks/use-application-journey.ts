import { useEffect, useRef, useState } from 'react';
import { getApplicationJourney, getSettledJourney, type ApplicationProgressSteps, type JourneyStep } from '@/lib/application-progress-animation';

export function useApplicationJourney(progress: ApplicationProgressSteps, paused: boolean) {
  const ref = useRef<HTMLOListElement>(null);
  const started = useRef(false);
  const settledProgress = useRef<ApplicationProgressSteps>([]);
  const [steps, setSteps] = useState<JourneyStep[]>(() => getApplicationJourney(progress)[0]?.steps ?? []);
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    if (paused) return;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const timers: number[] = [];
    let observer: IntersectionObserver | undefined;
    function clearTimers() { timers.forEach(timer => window.clearTimeout(timer)); timers.length = 0; }
    function finishImmediately() {
      clearTimers();
      setSteps(getSettledJourney(progress));
      settledProgress.current = progress;
      setSettled(true);
    }
    function play() {
      started.current = true;
      observer?.disconnect();
      if (media.matches) { finishImmediately(); return; }
      const frames = getApplicationJourney(progress, settledProgress.current);
      setSettled(false);
      setSteps(frames[0]?.steps ?? []);
      frames.slice(1).forEach((frame, index) => {
        timers.push(window.setTimeout(() => {
          setSteps(frame.steps);
          if (index === frames.length - 2) {
            settledProgress.current = progress;
            setSettled(true);
          }
        }, frame.delay));
      });
      if (frames.length === 1) finishImmediately();
    }
    function motionChanged() { if (media.matches) finishImmediately(); }
    media.addEventListener('change', motionChanged);
    if (media.matches || started.current || !('IntersectionObserver' in window)) play();
    else {
      observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) play();
      }, { threshold: 0, rootMargin: '0px 0px -40px 0px' });
      if (ref.current) observer.observe(ref.current.querySelector('.application-progress-node') ?? ref.current);
    }
    return () => {
      clearTimers();
      observer?.disconnect();
      media.removeEventListener('change', motionChanged);
    };
  }, [progress, paused]);

  return { ref, steps, settled };
}