import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { PlatformGuide } from '@/components/platform-guide';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

vi.mock('@tanstack/react-router', () => ({ useLocation: () => ({ pathname: '/dashboard' }) }));
vi.mock('@/components/sanad-layout', () => ({ Brand: () => null }));

function GuideState() {
  const state = useSanad();
  return <><output data-testid="guide-state">{String(state.guideOpen)}</output><button onClick={state.openGuide}>Request guide</button></>;
}

describe('Unobstructed dashboard entry', () => {
  it('keeps the guide closed until the candidate explicitly requests it', () => {
    render(<SanadProvider><PlatformGuide /><GuideState /></SanadProvider>);
    expect(screen.getByTestId('guide-state').textContent).toBe('false');
    fireEvent.click(screen.getByRole('button', { name: 'Request guide' }));
    expect(screen.getByTestId('guide-state').textContent).toBe('true');
    fireEvent.click(screen.getByRole('button', { name: 'إغلاق الدليل' }));
    expect(screen.getByTestId('guide-state').textContent).toBe('false');
  });
});