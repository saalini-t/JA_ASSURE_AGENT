import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from './App';
import { api } from './services/api';

vi.mock('./services/api', () => ({
  api: {
    getHealth: vi.fn(),
    getDashboardSummary: vi.fn(),
    getQueue: vi.fn(),
    getCompetitors: vi.fn(),
    getCompetitorDigests: vi.fn(),
    getLeads: vi.fn(),
    getLessons: vi.fn(),
    getFeedback: vi.fn(),
    getPublishingRecords: vi.fn(),
    getLinkedInAuthStatus: vi.fn(),
  },
  API_ORIGIN: 'http://localhost:8000',
  getMediaUrl: (p?: string) => p || '',
  linkedInLoginUrl: 'http://localhost:8000/api/v1/auth/linkedin/login',
}));

const mockedApi = vi.mocked(api, true);

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.getHealth.mockResolvedValue({
    status: 'ok', app_name: 'JA Assure', environment: 'test', database: 'connected',
    llm_mode: 'offline', supported_brands: ['jade', 'doctorshield', 'jaguartransit'],
  } as any);
  mockedApi.getDashboardSummary.mockResolvedValue({
    total_content: 0, pending_compliance: 0, pending_human_review: 0, compliance_approved: 0,
    human_approved: 0, approved: 0, rejected: 0, edited: 0, published: 0, rejection_rate: 0,
    average_compliance_score: 0, total_leads: 0, average_lead_score: 0, total_lessons_learned: 0,
    regeneration_count: 0, brand_breakdown: {}, platform_breakdown: {}, language_breakdown: {},
    feedback_reason_frequency: {},
  } as any);
  mockedApi.getQueue.mockResolvedValue([]);
  mockedApi.getCompetitors.mockResolvedValue([]);
  mockedApi.getCompetitorDigests.mockResolvedValue([]);
  mockedApi.getLeads.mockResolvedValue([]);
  mockedApi.getLessons.mockResolvedValue([]);
  mockedApi.getFeedback.mockResolvedValue([]);
  mockedApi.getPublishingRecords.mockResolvedValue([]);
  mockedApi.getLinkedInAuthStatus.mockResolvedValue({ oauth_configured: false, connected: false });
});

describe('App navigation', () => {
  it('loads the dashboard by default and can navigate to every tab, including the new Publishing tab', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => expect(mockedApi.getHealth).toHaveBeenCalled());
    expect(await screen.findByRole('heading', { name: /AI Marketing Command Center/i })).toBeInTheDocument();

    await user.click(screen.getByText('Publishing'));
    expect(await screen.findByText(/LinkedIn Publishing Dispatch/i)).toBeInTheDocument();

    await user.click(screen.getByText('Lead Intelligence'));
    expect(await screen.findByText(/B2B Lead Intelligence & Risk Underwriting Match/i)).toBeInTheDocument();

    await user.click(screen.getByText('Competitor Intel'));
    expect(await screen.findByText(/Competitor Change Digest/i)).toBeInTheDocument();

    await user.click(screen.getByText('Review Center'));
    expect(await screen.findByText(/Human Governance & Review Center/i)).toBeInTheDocument();
  });

  it('shows a retry option when the backend is unavailable, instead of crashing', async () => {
    mockedApi.getHealth.mockRejectedValue(new Error('Failed to fetch'));
    render(<App />);

    expect(await screen.findByText(/AI Marketing API Unavailable/i)).toBeInTheDocument();
    expect(screen.getByText(/Retry Connection/i)).toBeInTheDocument();
  });
});
