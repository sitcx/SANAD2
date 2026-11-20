/** Reading progress, independent of viewport size and scroll overshoot. */
export function getScrollProgress(scrollY: number, scrollHeight: number, viewportHeight: number): number {
  const distance = scrollHeight - viewportHeight;
  return distance > 0 ? Math.min(1, Math.max(0, scrollY / distance)) : 0;
}