import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { InterviewPreparation } from '@/components/interview-preparation';
import { MeetingRoom } from '@/components/meeting-room';
import { TooltipProvider } from '@/components/ui/tooltip';
import { SanadProvider, useSanad } from '@/lib/sanad-context';
import { jobs } from '@/lib/sanad-data';
import type { InterpreterChoice } from '@/lib/sign-interpreter';
import type { LocalMedia } from '@/hooks/use-local-media';

const cameraOnlyMedia = { videoRef: { current: null }, camera: false, busy: false, error: '' } as unknown as LocalMedia;

function InterpreterState() {
  const state = useSanad();
  return <output data-testid="interpreter-state">{String(state.interpreterRequested)}</output>;
}
function room(interpreter: InterpreterChoice) {
  window.scrollTo = vi.fn();
  return render(<SanadProvider><TooltipProvider><MeetingRoom job={jobs[0]} preview media={cameraOnlyMedia} candidateName="رند" interpreter={interpreter} /><InterpreterState /></TooltipProvider></SanadProvider>);
}
function recognise() {
  fireEvent.click(screen.getByRole('button', { name: /ابدأ الإشارة/ }));
  act(() => { vi.advanceTimersByTime(900); });
}

describe('Case 1: interpreter chosen before the interview', () => {
  it('disables the other interpreter once one is chosen and requires a choice to join', () => {
    window.scrollTo = vi.fn();
    const setInterpreter = vi.fn();
    const { rerender } = render(<SanadProvider><InterviewPreparation media={cameraOnlyMedia} name="رند" setName={() => {}} interpreter={null} setInterpreter={setInterpreter} job={jobs[0]} schedule={undefined} preview onJoin={() => {}} /></SanadProvider>);
    expect(screen.getByRole('button', { name: /ابدأ تجربة المقابلة/ })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: /مترجم الذكاء الاصطناعي/ }));
    expect(setInterpreter).toHaveBeenCalledWith('ai');
    rerender(<SanadProvider><InterviewPreparation media={cameraOnlyMedia} name="رند" setName={() => {}} interpreter="ai" setInterpreter={setInterpreter} job={jobs[0]} schedule={undefined} preview onJoin={() => {}} /></SanadProvider>);
    expect(screen.getByRole('button', { name: /مترجم بشري/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: /ابدأ تجربة المقابلة/ })).toBeEnabled();
    expect(screen.queryByRole('button', { name: /الميكروفون/ })).toBeNull();
  });

  it('starts with the human interpreter on stage when human was chosen', () => {
    room('human');
    expect(screen.getByText('اخترت مترجمًا بشريًا من البداية')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ابدأ الإشارة/ })).toBeNull();
    expect(screen.getByTestId('interpreter-state').textContent).toBe('true');
  });
});

describe('Case 2: AI interpreter shows sentence options', () => {
  it('sends the picked sentence to the recruiter', () => {
    vi.useFakeTimers();
    room('ai');
    recognise();
    const options = screen.getByRole('group', { name: 'الجمل المقترحة من إشارتك' });
    const first = options.querySelectorAll('button')[0]!;
    const text = first.textContent!;
    fireEvent.click(first);
    expect(document.querySelector('.meeting-approved-message')?.textContent).toContain(text);
    vi.useRealTimers();
  });
});

describe('Case 3: three "غير ذلك" presses switch to a human', () => {
  it('switches to a human interpreter automatically after the third miss', () => {
    vi.useFakeTimers();
    room('ai');
    recognise();
    for (let attempt = 0; attempt < 3; attempt++) {
      fireEvent.click(screen.getByRole('button', { name: /غير ذلك/ }));
      act(() => { vi.advanceTimersByTime(900); });
    }
    expect(screen.getByText('تم التحويل لمترجم بشري بعد ثلاث محاولات غير متطابقة')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /ابدأ الإشارة/ })).toBeNull();
    expect(screen.getByTestId('interpreter-state').textContent).toBe('true');
    vi.useRealTimers();
  });
});

describe('Case 4: manual request for a human, with confirmation', () => {
  it('asks for confirmation and only switches on yes', () => {
    room('ai');
    fireEvent.click(screen.getByRole('button', { name: 'مترجم بشري' }));
    expect(screen.getByText('هل أنت متأكد أنك تريد مترجمًا بشريًا؟')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /لا، أكمل مع الذكاء الاصطناعي/ }));
    expect(screen.getByTestId('interpreter-state').textContent).toBe('false');
    fireEvent.click(screen.getByRole('button', { name: 'مترجم بشري' }));
    fireEvent.click(screen.getByRole('button', { name: /نعم، أريد مترجمًا بشريًا/ }));
    expect(screen.getByText('تم التحويل لمترجم بشري بطلبك')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /المترجم البشري متصل/ })).toBeDisabled();
    expect(screen.getByTestId('interpreter-state').textContent).toBe('true');
  });

  it('keeps the question text on the stage below the interpreter notice', () => {
    const { container } = room('human');
    const stage = container.querySelector('.meeting-sign-stage');
    const notice = stage?.querySelector('.meeting-stage-notice');
    const captions = stage?.querySelector('.meeting-stage-captions');
    expect(notice).not.toBeNull();
    expect(captions).not.toBeNull();
    expect((notice!.compareDocumentPosition(captions!) & Node.DOCUMENT_POSITION_FOLLOWING) > 0).toBe(true);
  });
});

describe('Live Arabic captions (teammate feature)', () => {
  it('starts live Arabic captions of the interviewer with the room (case 2)', async () => {
    window.scrollTo = vi.fn();
    const getUserMedia = vi.fn().mockRejectedValue(new DOMException('Denied', 'NotAllowedError'));
    vi.stubGlobal('navigator', { ...navigator, mediaDevices: { getUserMedia } });
    vi.stubGlobal('AudioContext', class { state = 'running'; sampleRate = 48000; close() { return Promise.resolve(); } });
    render(<SanadProvider><TooltipProvider><MeetingRoom job={jobs[0]} preview media={cameraOnlyMedia} candidateName="رند" interpreter="ai" /></TooltipProvider></SanadProvider>);
    expect(screen.queryByText(/دعم بشري/)).toBeNull();
    await waitFor(() => expect(getUserMedia).toHaveBeenCalledOnce());
    expect(await screen.findByText(/لم يُسمح بالوصول إلى الميكروفون/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'الترجمة المباشرة غير متاحة' })).toBeDisabled();
    expect(screen.queryByRole('button', { name: /مترجم/ })).not.toBeNull();
    vi.unstubAllGlobals();
  });
});
