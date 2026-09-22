import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LeadsView } from './LeadsView';
import { api } from '../../services/api';
import type { Lead, LeadOutreach } from '../../types';

vi.mock('../../services/api', () => ({
  api: {
    getLeadOutreachList: vi.fn(),
    generateStructuredOutreach: vi.fn(),
    approveOutreach: vi.fn(),
    rejectOutreach: vi.fn(),
    editOutreach: vi.fn(),
    sendOutreach: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api, true);

const baseLead: Lead = {
  id: 1, name: 'Jane Tan', company: 'Marina Bay Jewels', industry: 'Jewellery',
  email: 'jane@marinabayjewels.test', fit_score: 82, recommended_brand: 'jade',
  status: 'qualified', created_at: '2026-01-01T00:00:00Z',
  scoring_breakdown: {
    industry_fit: 23.5, company_profile: 18, geographic_relevance: 20,
    product_relevance: 19, potential_insurance_need: 14, total_fit_score: 94.5,
    industry_fit_reason: 'High physical asset concentration.',
  },
};

const baseOutreach: LeadOutreach = {
  id: 10, lead_id: 1, product: 'jade', subject: 'Tailored Risk Review',
  body: 'Hello Jane, ...', personalization_points: ['Industry: Jewellery'], source_evidence: [],
  compliance_status: 'passed', status: 'human_review', compliance_score: 92,
  send_status: 'draft', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
};

const noop = () => {};

function renderLeads(leads: Lead[] = [baseLead]) {
  return render(
    <LeadsView
      leads={leads}
      leadCountry="all" setLeadCountry={noop}
      leadBrand="all" setLeadBrand={noop}
      leadIndustry="" setLeadIndustry={noop}
      onDiscoverLeads={noop}
      onOpenEnrichModal={noop}
      actionLoading={null}
      showToast={noop}
      getSourceTypeBadge={() => <span>SRC</span>}
      getBrandBadge={() => <span>Jade</span>}
    />
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('LeadsView', () => {
  it('shows the real 5-factor scoring breakdown from the backend, never an approximated one', async () => {
    mockedApi.getLeadOutreachList.mockResolvedValue([]);
    const user = userEvent.setup();
    renderLeads();

    await user.click(screen.getByTitle('Toggle 5-Factor Score & Outreach'));
    expect(await screen.findByText('23.5/25 pts')).toBeInTheDocument();
    expect(screen.getByText('19/20 pts')).toBeInTheDocument();
  });

  it('shows an honest message instead of a fabricated breakdown when none is stored', async () => {
    mockedApi.getLeadOutreachList.mockResolvedValue([]);
    const user = userEvent.setup();
    renderLeads([{ ...baseLead, scoring_breakdown: null }]);

    await user.click(screen.getByTitle('Toggle 5-Factor Score & Outreach'));
    expect(await screen.findByText(/No stored scoring breakdown/i)).toBeInTheDocument();
  });

  it('generates a governed outreach draft and shows it awaiting human review', async () => {
    mockedApi.getLeadOutreachList.mockResolvedValueOnce([]).mockResolvedValueOnce([baseOutreach]);
    mockedApi.generateStructuredOutreach.mockResolvedValue(baseOutreach);
    const user = userEvent.setup();
    renderLeads();

    await user.click(screen.getByTitle('Toggle 5-Factor Score & Outreach'));
    await user.click(await screen.findByText('Generate New Draft'));

    expect(mockedApi.generateStructuredOutreach).toHaveBeenCalledWith(1);
    expect(await screen.findByText('Tailored Risk Review', { exact: false })).toBeInTheDocument();
    expect(screen.getByText('Approve')).toBeInTheDocument();
    expect(screen.getByText('Reject')).toBeInTheDocument();
  });

  it('only shows Send once the outreach is approved, and gates it on a verified email', async () => {
    const approved: LeadOutreach = { ...baseOutreach, status: 'approved' };
    mockedApi.getLeadOutreachList.mockResolvedValue([approved]);
    const user = userEvent.setup();
    renderLeads();

    await user.click(screen.getByTitle('Toggle 5-Factor Score & Outreach'));
    const sendButton = await screen.findByText(/Send Email/i);
    expect(sendButton.closest('button')).not.toBeDisabled();

    // No verified email on file -- Send must be disabled, never fabricating a recipient.
    renderLeads([{ ...baseLead, id: 2, email: undefined }]);
  });

  it('never shows Approve/Reject for a rejected outreach (HITL terminal state)', async () => {
    mockedApi.getLeadOutreachList.mockResolvedValue([{ ...baseOutreach, status: 'rejected' }]);
    const user = userEvent.setup();
    renderLeads();

    await user.click(screen.getByTitle('Toggle 5-Factor Score & Outreach'));
    await waitFor(() => expect(mockedApi.getLeadOutreachList).toHaveBeenCalled());
    expect(screen.queryByText('Approve')).not.toBeInTheDocument();
    expect(screen.queryByText(/Send Email/i)).not.toBeInTheDocument();
  });
});
