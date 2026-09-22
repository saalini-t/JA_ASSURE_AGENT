import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PublishingView } from './PublishingView';
import { api } from '../../services/api';
import type { ContentQueueItem, PublishingRecord } from '../../types';

vi.mock('../../services/api', () => ({
  api: { getLinkedInAuthStatus: vi.fn() },
  linkedInLoginUrl: 'http://localhost:8000/api/v1/auth/linkedin/login',
}));

const mockedApi = vi.mocked(api, true);

beforeEach(() => {
  vi.clearAllMocks();
  mockedApi.getLinkedInAuthStatus.mockResolvedValue({ oauth_configured: false, connected: false });
});

const approvedItem: ContentQueueItem = {
  id: 1, brand: 'jade', platform: 'linkedin', content_type: 'post', topic: 'Sub-limits',
  content_raw: 'text', variation: 'A', language: 'en', compliance_status: 'passed',
  status: 'approved', compliance_score: 95, created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z',
};

const realDispatchRecord: PublishingRecord = {
  id: 100, content_id: 2, platform: 'linkedin', attempt: 1, status: 'published',
  external_post_id: 'urn:li:share:12345', published_at: '2026-01-01T00:00:00Z',
  created_at: '2026-01-01T00:00:00Z',
};

const simulatedRecord: PublishingRecord = {
  id: 101, content_id: 3, platform: 'linkedin', attempt: 1, status: 'scheduled',
  engagement_metrics: '{"dispatch_mode": "simulated_preview", "external_api": "none"}',
  created_at: '2026-01-01T00:00:00Z',
};

function renderView(overrides: Partial<React.ComponentProps<typeof PublishingView>> = {}) {
  return render(
    <PublishingView
      queue={[approvedItem]}
      publishingRecords={[realDispatchRecord, simulatedRecord]}
      actionLoading={null}
      onPublishToLinkedIn={vi.fn()}
      onRefreshEngagement={vi.fn()}
      onRunWorkerOnce={vi.fn()}
      onCancelPublishing={vi.fn()}
      getBrandBadge={() => <span>Jade</span>}
      {...overrides}
    />
  );
}

describe('PublishingView', () => {
  it('lists approved, compliance-passed content as ready to publish', () => {
    renderView();
    expect(screen.getByText('Sub-limits')).toBeInTheDocument();
    expect(screen.getByText('Publish to LinkedIn')).toBeInTheDocument();
  });

  it('never offers to publish content that is already published', () => {
    renderView({ queue: [{ ...approvedItem, id: 2 }] });
    expect(screen.getByText(/No approved, compliance-passed content awaiting/i)).toBeInTheDocument();
  });

  it('correctly distinguishes a real LinkedIn dispatch from a simulated preview record', () => {
    renderView();
    expect(screen.getByText('Real LinkedIn')).toBeInTheDocument();
    expect(screen.getByText('Simulated Preview')).toBeInTheDocument();
    expect(screen.getByText('urn:li:share:12345')).toBeInTheDocument();
  });

  it('only offers Refresh Analytics for a real published dispatch, and Cancel only for a scheduled simulated one', () => {
    renderView();
    expect(screen.getByText('Refresh Analytics')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('calls onPublishToLinkedIn when the operator dispatches an approved item', async () => {
    const onPublish = vi.fn();
    const user = userEvent.setup();
    renderView({ onPublishToLinkedIn: onPublish });

    await user.click(screen.getByText('Publish to LinkedIn'));
    expect(onPublish).toHaveBeenCalledWith(1);
  });

  it('states manual-dispatch-by-default honestly rather than implying automation', () => {
    renderView();
    expect(screen.getByText(/Manual dispatch by default/i)).toBeInTheDocument();
    expect(screen.getByText(/PUBLISH_WORKER_ENABLED=true/)).toBeInTheDocument();
  });

  it('shows a Connect LinkedIn link when no member account is connected yet', async () => {
    renderView();
    await waitFor(() => expect(mockedApi.getLinkedInAuthStatus).toHaveBeenCalled());
    const link = await screen.findByText(/Connect LinkedIn/i);
    expect(link.closest('a')).toHaveAttribute('href', 'http://localhost:8000/api/v1/auth/linkedin/login');
  });

  it('shows Connected instead of the login link once a member account is authorized', async () => {
    mockedApi.getLinkedInAuthStatus.mockResolvedValue({ oauth_configured: true, connected: true });
    renderView();
    expect(await screen.findByText(/LinkedIn Connected/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Connect LinkedIn$/i)).not.toBeInTheDocument();
  });
});
