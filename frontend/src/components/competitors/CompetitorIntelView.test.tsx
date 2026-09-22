import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CompetitorIntelView } from './CompetitorIntelView';
import { api } from '../../services/api';
import type { Competitor, CompetitorDigestEntry } from '../../types';

vi.mock('../../services/api', () => ({
  api: {
    getCompetitorDigests: vi.fn(),
    getCompetitorSnapshots: vi.fn(),
  },
}));

const mockedApi = vi.mocked(api, true);

const competitor: Competitor = {
  id: 1, name: 'BriteProtect', category: 'jewellery insurance', title: 'BriteProtect Policy',
  summary: 'Offers regional sub-limits.', relevance: 0.9, source: 'https://briteprotect.example.com',
  collected_at: '2026-01-01T00:00:00Z',
};

const digestEntry: CompetitorDigestEntry = {
  competitor_id: 1, competitor_name: 'BriteProtect', category: 'jewellery insurance',
  source_type: 'VERIFIED_SOURCE', has_change: true, changed_fields: ['summary'],
  previous_state: { summary: 'old' }, current_state: { summary: 'new' },
  detected_at: '2026-01-02T00:00:00Z', why_it_matters: 'They loosened sub-limits.',
  suggested_action: 'Counter-position with agreed-value coverage.',
};

const noop = () => {};

function renderView(competitors: Competitor[] = [competitor]) {
  return render(
    <CompetitorIntelView
      competitors={competitors}
      scrapeUrlInput="" setScrapeUrlInput={noop}
      scrapeBrand="jade" setScrapeBrand={noop}
      scrapeResult={null}
      actionLoading={null}
      onScrape={noop}
      getSourceTypeBadge={() => <span>SRC</span>}
    />
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('CompetitorIntelView', () => {
  it('renders real digest data instead of the old hardcoded whitespace opportunities', async () => {
    mockedApi.getCompetitorDigests.mockResolvedValue([digestEntry]);
    renderView();

    expect(await screen.findByText('BriteProtect')).toBeInTheDocument();
    expect(screen.getByText(/They loosened sub-limits/i)).toBeInTheDocument();
    expect(screen.getByText(/Counter-position with agreed-value coverage/i)).toBeInTheDocument();
    // The old component fabricated a fixed "94% Confidence" figure -- must be gone.
    expect(screen.queryByText(/94% Confidence/i)).not.toBeInTheDocument();
  });

  it('shows an honest empty state instead of fabricated opportunities when there is no digest yet', async () => {
    mockedApi.getCompetitorDigests.mockResolvedValue([]);
    renderView();

    expect(await screen.findByText(/No digest entries yet/i)).toBeInTheDocument();
  });

  it('loads and displays real snapshot history on demand', async () => {
    mockedApi.getCompetitorDigests.mockResolvedValue([]);
    mockedApi.getCompetitorSnapshots.mockResolvedValue([
      { id: 5, competitor_id: 1, source_type: 'VERIFIED_SOURCE', title: 'Old Title', summary: 'Old summary', captured_at: '2026-01-01T00:00:00Z' },
    ]);
    const user = userEvent.setup();
    renderView();

    await user.click(await screen.findByText(/Snapshot History/i));
    expect(await screen.findByText('Old summary')).toBeInTheDocument();
    expect(mockedApi.getCompetitorSnapshots).toHaveBeenCalledWith(1);
  });

  it('reports a load failure honestly instead of silently showing nothing', async () => {
    mockedApi.getCompetitorDigests.mockRejectedValue(new Error('network down'));
    renderView();

    await waitFor(() => expect(screen.getByText(/network down/i)).toBeInTheDocument());
  });
});
