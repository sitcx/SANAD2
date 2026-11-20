import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { LandingDock } from '@/components/landing-dock';
import { getScrollProgress } from '@/lib/scroll-progress';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('Circular home scroll progress', () => {
  it('tracks scrolling forward and backward through the page', () => {
    expect(getScrollProgress(0, 2000, 1000)).toBe(0);
    expect(getScrollProgress(250, 2000, 1000)).toBe(0.25);
    expect(getScrollProgress(500, 2000, 1000)).toBe(0.5);
    expect(getScrollProgress(1000, 2000, 1000)).toBe(1);
    expect(getScrollProgress(250, 2000, 1000)).toBe(0.25);
  });

  it('clamps overscroll and handles pages without scrolling', () => {
    expect(getScrollProgress(-50, 2000, 1000)).toBe(0);
    expect(getScrollProgress(1100, 2000, 1000)).toBe(1);
    expect(getScrollProgress(0, 800, 1000)).toBe(0);
    expect(getScrollProgress(0, 1000, 1000)).toBe(0);
  });

  it.each([false, true])('returns to the top respecting reduced motion: %s', reducedMotion => {
    vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: reducedMotion })));
    vi.stubGlobal('ResizeObserver', class {
      observe() {}
      disconnect() {}
    });
    vi.spyOn(window, 'scrollY', 'get').mockReturnValue(500);
    vi.spyOn(document.documentElement, 'scrollHeight', 'get').mockReturnValue(2000);
    const scrollTo = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
    render(<LandingDock />);
    fireEvent.click(screen.getByRole('button', { name: 'العودة إلى الأعلى' }));
    expect(scrollTo).toHaveBeenCalledWith({ top: 0, behavior: reducedMotion ? 'instant' : 'smooth' });
  });
});