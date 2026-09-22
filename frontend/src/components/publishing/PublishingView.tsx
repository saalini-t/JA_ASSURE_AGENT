import React, { useEffect, useState } from 'react';
import {
  Send,
  Zap,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Info,
  BarChart3,
  Link2,
  Check
} from 'lucide-react';
import type { ContentQueueItem, PublishingRecord } from '../../types';
import { api, linkedInLoginUrl } from '../../services/api';

interface PublishingViewProps {
  queue: ContentQueueItem[];
  publishingRecords: PublishingRecord[];
  actionLoading: string | null;
  onPublishToLinkedIn: (contentId: number) => void;
  onRefreshEngagement: (recordId: number) => void;
  onRunWorkerOnce: () => void;
  onCancelPublishing: (recordId: number) => void;
  getBrandBadge: (brand: string) => React.ReactNode;
}

// The simulated preview endpoint stamps this exact marker into engagement_metrics
// at creation time -- a real LinkedIn dispatch never does, so this is a genuine
// signal read from the data, not an inferred/fabricated label.
const isSimulatedRecord = (rec: PublishingRecord): boolean =>
  !!rec.engagement_metrics && rec.engagement_metrics.includes('simulated_preview');

const recordStatusBadge = (rec: PublishingRecord) => {
  const s = rec.status;
  const cls =
    s === 'published' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
    s === 'failed' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
    s === 'publishing' ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40' :
    s === 'cancelled' ? 'bg-slate-800 text-slate-400 border-slate-700' :
    'bg-amber-500/20 text-amber-300 border-amber-500/40';
  return <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${cls}`}>{s}</span>;
};

const parseEngagement = (raw?: string): { display: string; real: boolean } => {
  if (!raw) return { display: 'Not fetched yet', real: false };
  try {
    const parsed = JSON.parse(raw);
    if (parsed.source === 'unavailable') {
      return { display: `Unavailable: ${parsed.reason || 'not accessible'}`, real: false };
    }
    if (parsed.dispatch_mode === 'simulated_preview') {
      return { display: 'Simulated preview -- no external API call', real: false };
    }
    if (typeof parsed.likes === 'number' || typeof parsed.comments === 'number') {
      return { display: `${parsed.likes ?? 0} likes, ${parsed.comments ?? 0} comments`, real: true };
    }
    return { display: raw, real: false };
  } catch {
    return { display: raw, real: false };
  }
};

export const PublishingView: React.FC<PublishingViewProps> = ({
  queue,
  publishingRecords,
  actionLoading,
  onPublishToLinkedIn,
  onRefreshEngagement,
  onRunWorkerOnce,
  onCancelPublishing,
  getBrandBadge
}) => {
  const [linkedInStatus, setLinkedInStatus] = useState<{ oauth_configured: boolean; connected: boolean } | null>(null);

  useEffect(() => {
    api.getLinkedInAuthStatus().then(setLinkedInStatus).catch(() => setLinkedInStatus(null));
  }, []);

  const publishedContentIds = new Set(
    publishingRecords.filter((r) => r.status === 'published' && !isSimulatedRecord(r)).map((r) => r.content_id)
  );
  const readyToPublish = queue.filter(
    (item) => item.status === 'approved' && item.compliance_status === 'passed' && !publishedContentIds.has(item.id)
  );

  const sortedRecords = [...publishingRecords].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div className="space-y-6">
      {/* Header + honest automation status */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <Send className="w-4 h-4 text-blue-400" />
              LinkedIn Publishing Dispatch
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Every dispatch requires status='approved' AND compliance_status='passed' -- enforced server-side, not by this UI.
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {linkedInStatus?.connected ? (
              <span className="px-3 py-2 rounded-xl text-xs font-bold bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 flex items-center gap-2">
                <Check className="w-3.5 h-3.5" /> LinkedIn Connected (Member)
              </span>
            ) : (
              <a
                href={linkedInLoginUrl}
                className="px-3 py-2 rounded-xl bg-[#0A66C2] hover:brightness-110 text-white font-bold text-xs flex items-center gap-2 shadow-lg transition-all"
                title={linkedInStatus?.oauth_configured ? 'Authorize your personal LinkedIn account' : 'Set LINKEDIN_CLIENT_ID/SECRET/REDIRECT_URI in backend/.env first'}
              >
                <Link2 className="w-3.5 h-3.5" /> Connect LinkedIn
              </a>
            )}
            <button
              onClick={onRunWorkerOnce}
              disabled={actionLoading === 'worker-run'}
              className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5" />
              {actionLoading === 'worker-run' ? 'Running worker pass...' : 'Trigger Worker Pass (Manual)'}
            </button>
          </div>
        </div>
        <div className="flex items-start gap-2 p-3 rounded-xl bg-slate-900/70 border border-slate-800 text-[11px] text-slate-400">
          <Info className="w-3.5 h-3.5 text-cyan-400 shrink-0 mt-0.5" />
          <span>
            <strong className="text-slate-300">Manual dispatch by default.</strong> The button above and the "Publish"
            actions below each trigger exactly one dispatch pass through the same gated code path. Continuous automatic
            polling only runs if an operator has set <code className="text-cyan-300">PUBLISH_WORKER_ENABLED=true</code> in
            the backend's environment -- publishing to LinkedIn is never triggered automatically just because the server is running.
          </span>
        </div>
      </div>

      {/* Approved queue ready for dispatch */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          Approved & Ready to Publish ({readyToPublish.length})
        </h3>

        {readyToPublish.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">
            No approved, compliance-passed content awaiting LinkedIn dispatch. Approve items in the Review Center first.
          </div>
        ) : (
          <div className="space-y-2">
            {readyToPublish.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <div className="min-w-0 flex items-center gap-2 flex-wrap text-xs">
                  <span className="font-mono text-slate-500">#{item.id}</span>
                  {getBrandBadge(item.brand)}
                  <span className="text-slate-300 truncate max-w-md">{item.topic}</span>
                </div>
                <button
                  onClick={() => onPublishToLinkedIn(item.id)}
                  disabled={actionLoading === `linkedin-${item.id}`}
                  className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-500/40 flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shrink-0"
                >
                  <Send className="w-3.5 h-3.5" />
                  {actionLoading === `linkedin-${item.id}` ? 'Publishing...' : 'Publish to LinkedIn'}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Full dispatch record history -- real + simulated, honestly labeled */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Clock className="w-4 h-4 text-cyan-400" />
          Dispatch Record History ({publishingRecords.length})
        </h3>

        {sortedRecords.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">No publishing attempts recorded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] text-slate-400 uppercase font-mono border-b border-slate-800/80">
                <tr>
                  <th className="py-2.5 px-3">Record</th>
                  <th className="py-2.5 px-3">Content</th>
                  <th className="py-2.5 px-3">Mode</th>
                  <th className="py-2.5 px-3">Attempt</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">External Post ID</th>
                  <th className="py-2.5 px-3">Engagement</th>
                  <th className="py-2.5 px-3">Error</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {sortedRecords.map((rec) => {
                  const simulated = isSimulatedRecord(rec);
                  const engagement = parseEngagement(rec.engagement_metrics);
                  const canRefresh = !simulated && rec.status === 'published' && !!rec.external_post_id;
                  return (
                    <tr key={rec.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-3 px-3 font-mono font-semibold text-slate-300">#{rec.id}</td>
                      <td className="py-3 px-3 font-mono text-cyan-400">Item #{rec.content_id}</td>
                      <td className="py-3 px-3">
                        {simulated ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-400 border border-slate-700">
                            Simulated Preview
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-blue-500/15 text-blue-300 border border-blue-500/30">
                            Real LinkedIn
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono text-slate-400">{rec.attempt}</td>
                      <td className="py-3 px-3">{recordStatusBadge(rec)}</td>
                      <td className="py-3 px-3 font-mono text-slate-300">{rec.external_post_id || '—'}</td>
                      <td className="py-3 px-3">
                        <span className={engagement.real ? 'text-emerald-300' : 'text-slate-500'}>{engagement.display}</span>
                      </td>
                      <td className="py-3 px-3 text-rose-400 max-w-[16rem] truncate" title={rec.error_info}>
                        {rec.error_info || '—'}
                      </td>
                      <td className="py-3 px-3 text-right">
                        {canRefresh && (
                          <button
                            onClick={() => onRefreshEngagement(rec.id)}
                            disabled={actionLoading === `refresh-${rec.id}`}
                            className="px-2.5 py-1 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 text-[11px] transition-colors cursor-pointer inline-flex items-center gap-1"
                          >
                            <RefreshCw className={`w-3 h-3 ${actionLoading === `refresh-${rec.id}` ? 'animate-spin' : ''}`} />
                            Refresh Analytics
                          </button>
                        )}
                        {simulated && rec.status === 'scheduled' && (
                          <button
                            onClick={() => onCancelPublishing(rec.id)}
                            disabled={actionLoading === `cancel-pub-${rec.id}`}
                            className="px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[11px] transition-colors cursor-pointer"
                          >
                            Cancel
                          </button>
                        )}
                        {!canRefresh && !(simulated && rec.status === 'scheduled') && (
                          <span className="text-[11px] text-slate-600 font-mono">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {publishingRecords.some((r) => r.status === 'failed') && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-rose-950/30 border border-rose-800/50 text-[11px] text-rose-200">
          <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
          <span>Some dispatch attempts failed. Permanent failures (missing token, invalid asset) are not retried automatically; transient failures already retried with backoff before landing here.</span>
        </div>
      )}
      {publishingRecords.some((r) => !isSimulatedRecord(r) && r.status === 'published') && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-emerald-950/20 border border-emerald-800/40 text-[11px] text-emerald-200">
          <BarChart3 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
          <span>Engagement numbers shown above are only ever real values from a successful LinkedIn API response, or an honest "unavailable" -- never invented.</span>
        </div>
      )}
    </div>
  );
};
