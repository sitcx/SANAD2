import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { InterviewPreparation, interviewCommunicationChoices } from '@/components/interview-preparation';
import { MeetingRoom } from '@/components/meeting-room';
import { TooltipProvider } from '@/components/ui/tooltip';
import { SanadProvider, useSanad } from '@/lib/sanad-context';
import { jobs } from '@/lib/sanad-data';
import type { LocalMedia } from '@/hooks/use-local-media';

const cameraOnlyMedia = { videoRef: { current: null }, camera: false, busy: false, error: '' } as unknown as LocalMedia;

function InterpreterState() {
  const state = useSanad();
  return <output data-testid="interpreter-state">{String(state.interpreterRequested)}</output>;
}

describe('Interview communication without audio', () => {
  it('offers only sign language and writing as communication modes', () => {
    expect(interviewCommunicationChoices.map(item => item.id)).toEqual(['sign', 'text']);
    expect(interviewCommunicationChoices.map(item => item.label)).toEqual(['لغة الإشارة', 'الكتابة']);
  });

  it('prepares with a camera only and no microphone control', () => {
    window.scrollTo = vi.fn();
    render(<SanadProvider><InterviewPreparation media={cameraOnlyMedia} name="رند" setName={() => {}} communication="sign" setCommunication={() => {}} job={jobs[0]} schedule={undefined} preview onJoin={() => {}} /></SanadProvider>);
    expect(screen.queryByRole('button', { name: /الميكروفون/ })).toBeNull();
    expect(screen.getAllByRole('button', { name: /الكاميرا/ }).length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: 'الصوت' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'النص والصوت' })).toBeNull();
  });

  it('shows the interpreter need as a labeled control and records the request', () => {
    window.scrollTo = vi.fn();
    render(<SanadProvider><TooltipProvider><MeetingRoom job={jobs[0]} preview media={cameraOnlyMedia} candidateName="رند" communication="sign" /><InterpreterState /></TooltipProvider></SanadProvider>);
    expect(screen.getByTestId('interpreter-state').textContent).toBe('false');
    fireEvent.click(screen.getByRole('button', { name: /الحاجة إلى مترجم/ }));
    expect(screen.getByTestId('interpreter-state').textContent).toBe('true');
    expect(screen.getByText('طلب المترجم مسجّل في هذه الجلسة · غير متصل في النموذج')).toBeInTheDocument();
  });

  it('keeps only the question text on the stage and puts the interpreter request above it', () => {
    window.scrollTo = vi.fn();
    const { container } = render(<SanadProvider><TooltipProvider><MeetingRoom job={jobs[0]} preview media={cameraOnlyMedia} candidateName="رند" communication="sign" /></TooltipProvider></SanadProvider>);
    expect(screen.queryByText('ترجمة كلام مسؤول التوظيف')).toBeNull();
    expect(screen.queryByText('مساحة لغة الإشارة · الفيديو غير متاح حاليًا')).toBeNull();
    const stage = container.querySelector('.meeting-sign-stage');
    expect(stage).not.toBeNull();
    expect(stage?.querySelector('.meeting-stage-notice')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: /الحاجة إلى مترجم/ }));
    const notice = stage?.querySelector('.meeting-stage-notice');
    const captions = stage?.querySelector('.meeting-stage-captions');
    expect(notice).not.toBeNull();
    expect(captions).not.toBeNull();
    expect((notice!.compareDocumentPosition(captions!) & Node.DOCUMENT_POSITION_FOLLOWING) > 0).toBe(true);
  });

  it('has no human support entry and no microphone control in the room', () => {
    window.scrollTo = vi.fn();
    render(<SanadProvider><TooltipProvider><MeetingRoom job={jobs[0]} preview media={cameraOnlyMedia} candidateName="رند" communication="sign" /></TooltipProvider></SanadProvider>);
    expect(screen.queryByText(/دعم بشري/)).toBeNull();
    expect(screen.queryByRole('button', { name: /الميكروفون/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /مترجم/ })).not.toBeNull();
  });
});
