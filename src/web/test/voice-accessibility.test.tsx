import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SpeakButton } from '@/components/speak-button';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

function ModeSwitch() {
  const state = useSanad();
  return <><button onClick={() => state.setCommunicationMode('voice')}>voice</button><button onClick={() => state.setLargeText(true)}>large</button></>;
}

describe('voice accessibility', () => {
  it('shows speaker buttons only in voice mode and reads the section aloud', () => {
    const speakMock = vi.fn();
    class Utterance { lang = ''; rate = 1; constructor(public text: string) {} }
    Object.assign(window, { speechSynthesis: { speak: speakMock, cancel: vi.fn() }, SpeechSynthesisUtterance: Utterance });
    render(<SanadProvider><ModeSwitch /><SpeakButton label="الوظيفة" text="محلل بيانات" /></SanadProvider>);
    expect(screen.queryByRole('button', { name: 'استمع: الوظيفة' })).toBeNull();
    act(() => { fireEvent.click(screen.getByText('voice')); });
    fireEvent.click(screen.getByRole('button', { name: 'استمع: الوظيفة' }));
    expect(speakMock).toHaveBeenCalledWith(expect.objectContaining({ text: 'محلل بيانات', lang: 'ar-SA' }));
  });

  it('turns on the large text mode for low vision', () => {
    render(<SanadProvider><ModeSwitch /></SanadProvider>);
    act(() => { fireEvent.click(screen.getByText('large')); });
    expect(document.documentElement.classList.contains('a11y-large')).toBe(true);
  });
});
