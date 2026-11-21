import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Route } from '@/routes/company';
import { SanadProvider, useSanad } from '@/lib/sanad-context';

const api = vi.hoisted(() => ({
  jobs: vi.fn(async () => [{ id: 'analyst', company: 'بُعد', title: 'محلل بيانات', city: 'الرياض', mode: 'هجين', salary: null, description: null, skills: ['Excel', 'SQL'], min_years: 1, applicants: 1 }]),
  indicators: vi.fn(async () => ({ postings: 12, applicants: 25, average_match: 74, interview_rate: 48, hired: 6, retention: 83, by_mode: { sign: { applicants: 15, hired: 4 }, voice: { applicants: 10, hired: 2 } } })),
  candidates: vi.fn(async () => [{ talent: { id: 'c1', name: 'نورة', mode: 'sign', years: 3, city: 'الرياض', skills: ['Excel', 'SQL'] }, status: 'applied', interview_at: null, match: 100, suggested: false }]),
  setStatus: vi.fn(async () => ({})),
  schedule: vi.fn(), createJob: vi.fn(), setMinYears: vi.fn(), reset: vi.fn(),
}));
vi.mock('@/lib/company-api', async importOriginal => ({ ...(await importOriginal<object>()), companyApi: api }));

function AsCompany() {
  const state = useSanad();
  return <button onClick={() => state.signIn('شركة بُعد', '', undefined, 'company')}>company</button>;
}

describe('company dashboard', () => {
  it('shows indicators and candidates from the API and saves a decision', async () => {
    const Page = Route.options.component!;
    render(<SanadProvider><AsCompany /><Page /></SanadProvider>);
    act(() => { fireEvent.click(screen.getByText('company')); });
    expect(await screen.findByText('٨٣٪')).toBeInTheDocument();
    expect(await screen.findByText('نورة')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'ترشيح للمقابلة' }));
    await waitFor(() => expect(api.setStatus).toHaveBeenCalledWith('analyst', 'c1', 'nominated'));
    expect(api.jobs.mock.calls.length).toBeGreaterThan(1);   // numbers reloaded after the change
  });
});
