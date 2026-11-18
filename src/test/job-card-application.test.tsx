import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { JobCard } from '@/components/job-card';
import { jobs } from '@/lib/sanad-data';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

vi.mock('@tanstack/react-router', () => ({
  Link: ({ children }: { children: ReactNode }) => <a>{children}</a>,
}));

function ApplicationState() {
  const state = useSanad();
  return <output data-testid="application-state">{JSON.stringify({
    applications: state.applications,
    history: state.applicationHistory['designer']?.map(item => item.status),
    selectedJobId: state.selectedJobId,
  })}</output>;
}

describe('Applying from an unsubmitted job card', () => {
  it('submits the available job into the shared session without changing other applications', () => {
    const job = jobs.find(item => item.id === 'designer');
    if (!job) throw new Error('Missing available designer fixture');
    render(<SanadProvider><JobCard job={job} /><ApplicationState /></SanadProvider>);
    fireEvent.click(screen.getByRole('button', { name: 'التقديم على الوظيفة' }));
    expect(JSON.parse(screen.getByTestId('application-state').textContent ?? '{}')).toEqual({
      applications: { analyst: 'nominated', support: 'nominated', designer: 'applied' },
      history: ['applied'],
      selectedJobId: 'designer',
    });
  });
});