import { useEffect, useState } from 'react';
import { ArrowUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getScrollProgress } from '@/lib/scroll-progress';

/** A stationary arrow with a clockwise reading-progress edge. */
export function LandingDock() {
  const [status, setStatus] = useState({ shown: false, progress: 0 });

  useEffect(() => {
    let frame = 0;
    function read() {
      frame = 0;
      const progress = getScrollProgress(window.scrollY, document.documentElement.scrollHeight, window.innerHeight);
      setStatus(previous => {
        const next = { shown: window.scrollY > 240, progress };
        const same = previous.shown === next.shown && previous.progress === next.progress;
        return same ? previous : next;
      });
    }
    function onScroll() {
      if (!frame) frame = requestAnimationFrame(read);
    }
    read();
    const observer = new ResizeObserver(onScroll);
    observer.observe(document.documentElement);
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
    };
  }, []);

  if (!status.shown) return null;

  return <Button variant="outline" size="icon" className="landing-scroll-top"
    aria-label="العودة إلى الأعلى" title="العودة إلى الأعلى"
    onClick={() => window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' })}>
    <svg className="landing-scroll-ring" viewBox="0 0 56 56" aria-hidden="true">
      <circle className="landing-scroll-track" cx="28" cy="28" r="25" />
      <circle className="landing-scroll-fill" cx="28" cy="28" r="25" pathLength="100"
        strokeDasharray="100" strokeDashoffset={100 * (1 - status.progress)} />
    </svg>
    <ArrowUp className="landing-scroll-arrow" aria-hidden="true" />
  </Button>;
}
