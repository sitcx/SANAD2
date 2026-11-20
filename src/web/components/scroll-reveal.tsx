import { useEffect, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

/** Reveal once on arrival, with a visible fallback if observation is unavailable. */
export function ScrollReveal({ children, className, label }: { children: ReactNode; className?: string; label: string }) {
  const ref = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        setVisible(true);
        observer.disconnect();
      }
    }, { threshold: 0, rootMargin: '0px 0px -64px 0px' });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return <section ref={ref} aria-labelledby={label} className={cn('landing-section scroll-reveal', className)} data-revealed={visible}>
    {children}
  </section>;
}