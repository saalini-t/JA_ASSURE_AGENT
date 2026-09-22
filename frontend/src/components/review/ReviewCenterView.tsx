import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Check, 
  X, 
  Wand2, 
  FileText, 
  RefreshCw, 
  Calendar, 
  CheckCircle2, 
  XCircle, 
  Clock,
  AlertCircle,
  Scale,
  Globe,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  History,
  UserCheck,
  ArrowRight
} from 'lucide-react';
import type { ContentQueueItem, ComplianceViolation, ClaimItem, ReviewDecisionItem } from '../../types';
import { api } from '../../services/api';

interface ReviewCenterViewProps {
  queue: ContentQueueItem[];
  reviewFilter: 'pending' | 'approved' | 'rejected' | 'all';
  setReviewFilter: (filter: 'pending' | 'approved' | 'rejected' | 'all') => void;
  onApprove: (id: number) => void;
  onOpenReject: (item: ContentQueueItem) => void;
  onOpenEdit: (item: ContentQueueItem) => void;
  onRewrite: (id: number) => void;
  onRegenerate: (id: number) => void;
  onOpenScheduleModal: (item: ContentQueueItem) => void;
  actionLoading: string | null;
  getBrandBadge: (brand: string) => React.ReactNode;
  getStatusBadge: (status: string) => React.ReactNode;
}

interface ParsedMetadata {
  compliance_status?: string;
  compliance_score?: number;
  compliance_jurisdiction?: string;
  compliance_product?: string;
  compliance_disclaimer_status?: string;
  compliance_violations?: ComplianceViolation[];
  compliance_warnings?: ComplianceViolation[];
  claims_analyzed?: ClaimItem[];
  audit_trail?: Array<{ action: string; timestamp: string; previous_score?: number; new_score?: number }>;
}

function parseMetadata(jsonStr?: string): ParsedMetadata | null {
  if (!jsonStr) return null;
  try {
    return JSON.parse(jsonStr);
  } catch {
    return null;
  }
}

export const ReviewCenterView: React.FC<ReviewCenterViewProps> = ({
  queue,
  reviewFilter,
  setReviewFilter,
  onApprove,
  onOpenReject,
  onOpenEdit,
  onRewrite,
  onRegenerate,
  onOpenScheduleModal,
  actionLoading,
  getBrandBadge,
  getStatusBadge
}) => {
  const [expandedAudits, setExpandedAudits] = useState<Record<number, boolean>>({});
  const [historyModalItem, setHistoryModalItem] = useState<ContentQueueItem | null>(null);
  const [historyItems, setHistoryItems] = useState<ReviewDecisionItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const toggleAudit = (id: number) => {
    setExpandedAudits(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleOpenHistory = async (item: ContentQueueItem) => {
    setHistoryModalItem(item);
    setHistoryLoading(true);
    try {
      const data = await api.getReviewHistory(item.id);
      setHistoryItems(data);
    } catch (err) {
      console.error('Failed to fetch review history:', err);
      setHistoryItems([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const pendingCount = queue.filter(q => q.status === 'human_review' || q.status === 'pending').length;
  const approvedCount = queue.filter(q => q.status === 'approved' || q.status === 'scheduled' || q.status === 'published').length;
  const rejectedCount = queue.filter(q => q.status === 'rejected').length;

  const filteredQueue = queue.filter(item => {
    if (reviewFilter === 'pending') return item.status === 'human_review' || item.status === 'pending';
    if (reviewFilter === 'approved') return item.status === 'approved' || item.status === 'scheduled' || item.status === 'published';
    if (reviewFilter === 'rejected') return item.status === 'rejected';
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Compliance Control Room Header */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Human Governance & Editorial Gate
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Strict human approval required for every generated asset. Rejections synthesize permanent prompt guardrails.
          </p>
        </div>

        {/* Filter Chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setReviewFilter('all')}
            className={`px-3 py-1.5 rounded-xl text-xs font-mono font-medium transition-all cursor-pointer ${
              reviewFilter === 'all' 
                ? 'bg-slate-800 text-slate-100 border border-slate-700 shadow-sm' 
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All Items ({queue.length})
          </button>

          <button
            onClick={() => setReviewFilter('pending')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              reviewFilter === 'pending' 
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40 shadow-sm shadow-amber-500/10' 
                : 'text-slate-400 hover:text-amber-300'
            }`}
          >
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            Pending Review ({pendingCount})
          </button>

          <button
            onClick={() => setReviewFilter('approved')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              reviewFilter === 'approved' 
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-500/10' 
                : 'text-slate-400 hover:text-emerald-300'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            Approved ({approvedCount})
          </button>

          <button
            onClick={() => setReviewFilter('rejected')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-mono font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
              reviewFilter === 'rejected' 
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40 shadow-sm shadow-rose-500/10' 
                : 'text-slate-400 hover:text-rose-300'
            }`}
          >
            <XCircle className="w-3.5 h-3.5 text-rose-400" />
            Rejected ({rejectedCount})
          </button>
        </div>
      </div>

      {/* Queue List Cards */}
      <div className="space-y-4">
        {filteredQueue.length === 0 ? (
          <div className="glass-panel p-16 rounded-2xl border border-slate-800 text-center space-y-2">
            <CheckCircle2 className="w-8 h-8 text-slate-600 mx-auto" />
            <h4 className="text-sm font-semibold text-slate-200">No content in this review filter</h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {reviewFilter === 'pending'
                ? 'All generated marketing items have been evaluated. Excellent governance compliance!'
                : 'Generate drafts in the Content Studio to populate the review queue.'}
            </p>
          </div>
        ) : (
          filteredQueue.map((item) => {
            const isApproved = item.status === 'approved' || item.status === 'scheduled' || item.status === 'published';
            const isPending = item.status === 'human_review' || item.status === 'pending';
            const isRejected = item.status === 'rejected';

            const parsedMeta = parseMetadata(item.metadata_json);
            const violations: ComplianceViolation[] = parsedMeta?.compliance_violations || [];
            const warnings: ComplianceViolation[] = parsedMeta?.compliance_warnings || [];
            const allViolations = [...violations, ...warnings];
            
            // If no structured violations from metadata, construct one from reason_tag if present
            if (allViolations.length === 0 && item.reason_tag && item.reason_tag !== 'none' && item.reason_tag !== 'human_edit') {
              allViolations.push({
                rule_id: item.reason_tag,
                severity: item.compliance_score < 60 ? 'CRITICAL' : 'HIGH',
                message: item.notes || 'Compliance rule flag triggered',
                reason: item.notes || 'Identified non-compliant phrasing in draft'
              });
            }

            const rawStatus = (parsedMeta?.compliance_status || (
              item.compliance_score >= 85 ? 'PASS' :
              item.compliance_score < 60 ? 'BLOCKED' : 'WARNING'
            )).toUpperCase();

            const isBlocked = rawStatus === 'BLOCKED' || item.compliance_status === 'failed' || item.compliance_score < 60;
            const isWarning = rawStatus === 'WARNING' || (!isBlocked && item.compliance_score < 85);
            const isPass = !isBlocked && !isWarning;

            return (
              <div 
                key={item.id} 
                className={`glass-panel p-6 rounded-2xl border transition-all space-y-4 ${
                  isPending ? 'border-amber-500/30 hover:border-amber-500/50 bg-[#0e1628]/70' :
                  isApproved ? 'border-emerald-500/20 hover:border-emerald-500/40' :
                  'border-rose-500/20 hover:border-rose-500/40'
                }`}
              >
                {/* Item Meta Header */}
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    {getBrandBadge(item.brand)}
                    <span className="px-2.5 py-0.5 rounded text-xs bg-slate-800/90 text-slate-300 capitalize font-mono border border-slate-700">
                      {item.platform}
                    </span>
                    <span className="px-2 py-0.5 rounded text-xs bg-slate-800/60 text-slate-400 uppercase font-mono">
                      Var {item.variation} • {item.language}
                    </span>
                    <span className="text-[11px] font-mono text-slate-500">#{item.id}</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono text-slate-400">Compliance Audit:</span>
                    <span className={`text-xs font-bold font-mono px-2.5 py-0.5 rounded-full ${
                      item.compliance_score >= 85 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                      item.compliance_score >= 60 ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' :
                      'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                    }`}>
                      {item.compliance_score}%
                    </span>
                    <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-md uppercase tracking-wider ${
                      isPass ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                      isBlocked ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                      'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                    }`}>
                      {rawStatus}
                    </span>
                    {getStatusBadge(item.status)}
                  </div>
                </div>

                {/* Content Raw & Topic */}
                <div className="space-y-2">
                  <h4 className="font-bold text-sm text-slate-100">{item.topic}</h4>
                  <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed bg-[#0a0f1d] p-4 rounded-xl border border-slate-800/80 font-sans selection:bg-amber-500 selection:text-slate-950">
                    {item.content_raw}
                  </p>
                </div>

                {/* Compliance Audit Inspector Card */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-4 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5 font-mono">
                        <Scale className="w-3.5 h-3.5 text-cyan-400" />
                        Regulatory Governance Audit
                      </span>
                      <span className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        isPass ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' :
                        isBlocked ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' :
                        'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      }`}>
                        {rawStatus}
                      </span>
                      <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/80 flex items-center gap-1">
                        <Globe className="w-3 h-3 text-indigo-400" />
                        {parsedMeta?.compliance_jurisdiction || 'SG / MAS'}
                      </span>
                      {parsedMeta?.compliance_product && (
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/50">
                          {parsedMeta.compliance_product}
                        </span>
                      )}
                      {parsedMeta?.compliance_disclaimer_status && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800/60 text-slate-400">
                          Disclaimer: {parsedMeta.compliance_disclaimer_status}
                        </span>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => toggleAudit(item.id)}
                      className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer transition-colors"
                    >
                      {expandedAudits[item.id] ? (
                        <>Hide Audit Breakdown <ChevronUp className="w-3.5 h-3.5" /></>
                      ) : (
                        <>
                          Inspect Audit Breakdown
                          {allViolations.length > 0 && ` (${allViolations.length})`}
                          <ChevronDown className="w-3.5 h-3.5" />
                        </>
                      )}
                    </button>
                  </div>

                  {/* Collapsed Snippet if violations exist */}
                  {!expandedAudits[item.id] && allViolations.length > 0 && (
                    <div className="flex items-center gap-2 text-xs text-rose-300 bg-rose-950/30 px-3 py-1.5 rounded-lg border border-rose-800/40">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                      <span className="truncate">
                        <strong>{allViolations[0].rule_id}</strong>: {allViolations[0].reason || allViolations[0].message}
                      </span>
                      {allViolations.length > 1 && (
                        <span className="text-[10px] bg-rose-900/60 px-1.5 py-0.5 rounded text-rose-200 shrink-0 font-mono">
                          +{allViolations.length - 1} more
                        </span>
                      )}
                    </div>
                  )}

                  {/* Expanded Breakdown */}
                  {expandedAudits[item.id] && (
                    <div className="space-y-3 pt-2 border-t border-slate-800/60">
                      {allViolations.length === 0 ? (
                        <div className="text-xs text-emerald-300 bg-emerald-950/20 p-3 rounded-lg border border-emerald-800/30 flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                          <span>Zero regulatory violations detected across 12 statutory rule categories. Ready for human review sign-off.</span>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                            Detected Regulatory Violations & Remediations ({allViolations.length})
                          </div>
                          {allViolations.map((v, vIdx) => {
                            const sev = (v.severity || 'MEDIUM').toUpperCase();
                            const sevBadgeStyle = 
                              sev === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/50 font-bold' :
                              sev === 'HIGH' ? 'bg-orange-500/20 text-orange-300 border-orange-500/50 font-bold' :
                              sev === 'MEDIUM' ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' :
                              'bg-blue-500/20 text-blue-300 border-blue-500/40';

                            return (
                              <div key={vIdx} className="p-3 rounded-xl bg-[#090d19] border border-slate-800 space-y-1.5 text-xs">
                                <div className="flex items-center justify-between gap-2 flex-wrap">
                                  <div className="flex items-center gap-2">
                                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${sevBadgeStyle}`}>
                                      {sev}
                                    </span>
                                    <span className="font-mono font-bold text-slate-200">{v.rule_id}</span>
                                    {v.category && (
                                      <span className="text-[10px] text-slate-400 capitalize">({v.category.replace(/_/g, ' ')})</span>
                                    )}
                                  </div>
                                </div>

                                {(v.matched_text || v.flagged_phrase) && (
                                  <div className="text-[11px] font-mono text-rose-300 bg-rose-950/30 px-2.5 py-1 rounded border border-rose-900/30">
                                    <span className="text-slate-400">Flagged phrase: </span>
                                    <span className="text-rose-200 font-semibold underline decoration-rose-500">
                                      "{v.matched_text || v.flagged_phrase}"
                                    </span>
                                  </div>
                                )}

                                <div className="text-slate-300 text-xs">
                                  <span className="text-slate-400 font-medium">Reason: </span>
                                  {v.reason || v.message}
                                </div>

                                {(v.recommendation || v.suggested_fix) && (
                                  <div className="text-emerald-300 text-xs bg-emerald-950/20 p-2 rounded border border-emerald-900/30">
                                    <span className="text-emerald-400 font-bold">Suggested Remediation: </span>
                                    {v.recommendation || v.suggested_fix}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Claims Analyzed Section */}
                      {parsedMeta?.claims_analyzed && parsedMeta.claims_analyzed.length > 0 && (
                        <div className="pt-2 border-t border-slate-800/50 space-y-1.5">
                          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                            Claims Analyzed ({parsedMeta.claims_analyzed.length})
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {parsedMeta.claims_analyzed.map((claim, cIdx) => (
                              <div key={cIdx} className="text-[11px] font-mono px-2 py-1 rounded bg-slate-800/80 border border-slate-700/60 text-slate-300 flex items-center gap-1.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${
                                  claim.risk_level === 'high' ? 'bg-rose-400' : claim.risk_level === 'medium' ? 'bg-amber-400' : 'bg-emerald-400'
                                }`} />
                                <span className="max-w-xs truncate">"{claim.claim_text}"</span>
                                <span className="text-[9px] uppercase px-1 rounded bg-slate-900 text-slate-400">{claim.claim_type}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Audit / Reviewer Notes if present */}
                {item.notes && (
                  <div className="text-xs text-slate-300 bg-slate-900/60 p-3 rounded-xl border border-slate-800 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-slate-200">Reviewer Guidance Note:</span>
                      <p className="text-slate-400 mt-0.5">{item.notes}</p>
                    </div>
                  </div>
                )}

                {/* Actions Toolbar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/80">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-500">
                      Staged {new Date(item.created_at).toLocaleString()}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleOpenHistory(item)}
                      className="px-2.5 py-1 rounded-lg text-[11px] font-mono text-slate-400 hover:text-cyan-300 hover:bg-slate-800/80 border border-slate-700/60 flex items-center gap-1.5 transition-colors cursor-pointer"
                      title="View Human Governance Decision Audit Trail"
                    >
                      <History className="w-3.5 h-3.5 text-cyan-400" />
                      Audit Trail
                    </button>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    {/* For Approved Items: Schedule Dispatch Preview */}
                    {isApproved && (
                      <button
                        onClick={() => onOpenScheduleModal(item)}
                        className="px-4 py-2 rounded-xl text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white flex items-center gap-1.5 shadow-md shadow-cyan-600/20 transition-all cursor-pointer"
                      >
                        <Calendar className="w-3.5 h-3.5" />
                        {item.status === 'scheduled' ? 'Reschedule Preview' : 'Schedule Dispatch Preview'}
                      </button>
                    )}

                    {/* Auto Compliance Rewrite - available for pending items with compliance issues */}
                    {isPending && (item.compliance_score < 85 || isBlocked || allViolations.length > 0) && (
                      <button
                        onClick={() => onRewrite(item.id)}
                        disabled={actionLoading === `rewrite-${item.id}`}
                        className="px-3.5 py-1.5 rounded-xl text-xs font-medium bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/40 flex items-center gap-1.5 transition-colors cursor-pointer shadow-sm shadow-indigo-600/10"
                      >
                        <Wand2 className="w-3.5 h-3.5 text-indigo-400" />
                        {actionLoading === `rewrite-${item.id}` ? 'Rewriting & Re-verifying...' : 'AI Rewrite Fix'}
                      </button>
                    )}

                    {/* Edit in place — only legal on items still awaiting human review (server-enforced) */}
                    {isPending && (
                      <button
                        onClick={() => onOpenEdit(item)}
                        className="px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
                      >
                        <FileText className="w-3.5 h-3.5" /> Edit Copy
                      </button>
                    )}

                    {/* Regenerate with lessons (for pending or rejected items) */}
                    {(isPending || isRejected) && (
                      <button
                        onClick={() => onRegenerate(item.id)}
                        disabled={actionLoading === `regen-${item.id}`}
                        className="px-3 py-1.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
                      >
                        <RefreshCw className="w-3.5 h-3.5" /> Regenerate
                      </button>
                    )}

                    {/* Reject & Learn - DISTINCT ROSE COLOR */}
                    {isPending && (
                      <button
                        onClick={() => onOpenReject(item)}
                        className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-rose-600/20 hover:bg-rose-600 text-rose-300 hover:text-white border border-rose-500/40 flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                      >
                        <X className="w-3.5 h-3.5" /> Reject & Learn
                      </button>
                    )}

                    {/* Approve - DISTINCT EMERALD COLOR */}
                    {isPending && (
                      <button
                        onClick={() => onApprove(item.id)}
                        disabled={actionLoading === `approve-${item.id}`}
                        className="px-4 py-1.5 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
                      >
                        <Check className="w-3.5 h-3.5" /> Approve
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* HITL Audit History Modal */}
      {historyModalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="bg-[#0b101b] border border-slate-700 w-full max-w-2xl rounded-2xl p-6 shadow-2xl space-y-5 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
                  <History className="w-4 h-4 text-cyan-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                    HITL Governance Audit Trail
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300">
                      Item #{historyModalItem.id}
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Immutable log of reviewer decisions, status transitions, and copy alterations.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setHistoryModalItem(null)}
                className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto space-y-4 pr-1 flex-1">
              {historyLoading ? (
                <div className="py-12 text-center text-slate-400 text-xs font-mono flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                  Fetching governance audit log...
                </div>
              ) : historyItems.length === 0 ? (
                <div className="py-12 text-center text-slate-400 text-xs">
                  <Clock className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                  No review decisions recorded yet. Content is currently in initial staging.
                </div>
              ) : (
                <div className="relative pl-6 border-l-2 border-slate-800 space-y-6">
                  {historyItems.map((dec, idx) => {
                    const decisionColor =
                      dec.decision === 'approve' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40' :
                      dec.decision === 'reject' ? 'bg-rose-500/20 text-rose-300 border-rose-500/40' :
                      dec.decision === 'edit' ? 'bg-sky-500/20 text-sky-300 border-sky-500/40' :
                      dec.decision === 'rewrite' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' :
                      'bg-purple-500/20 text-purple-300 border-purple-500/40';

                    return (
                      <div key={dec.id || idx} className="relative group">
                        <div className="absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full bg-[#0b101b] border-2 border-cyan-400 group-hover:scale-110 transition-transform" />

                        <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2.5">
                          <div className="flex items-center justify-between gap-2 flex-wrap text-xs">
                            <div className="flex items-center gap-2">
                              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono uppercase border ${decisionColor}`}>
                                {dec.decision}
                              </span>
                              <span className="font-mono text-slate-300 flex items-center gap-1">
                                <UserCheck className="w-3.5 h-3.5 text-slate-400" />
                                {dec.reviewer || 'compliance_officer'}
                              </span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-500">
                              {new Date(dec.created_at).toLocaleString()}
                            </span>
                          </div>

                          <div className="text-xs font-mono text-slate-400 flex items-center gap-1.5 flex-wrap">
                            <span>Status transition:</span>
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">{dec.previous_status}</span>
                            <ArrowRight className="w-3 h-3 text-slate-500" />
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-emerald-300">{dec.new_status}</span>
                            {dec.compliance_score !== null && dec.compliance_score !== undefined && (
                              <span className="ml-auto text-[11px] font-mono text-cyan-300 bg-cyan-950/40 border border-cyan-800/40 px-2 py-0.5 rounded">
                                Score: {dec.compliance_score.toFixed(1)}/100
                              </span>
                            )}
                          </div>

                          {(dec.reason_tag || dec.notes) && (
                            <div className="text-xs text-slate-300 bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80 space-y-1">
                              {dec.reason_tag && (
                                <div className="font-mono text-[11px] text-amber-300 font-semibold">
                                  Reason: {dec.reason_tag}
                                </div>
                              )}
                              {dec.notes && <p className="text-slate-400 text-xs">{dec.notes}</p>}
                            </div>
                          )}

                          {dec.edited_content && dec.edited_content !== dec.original_content && (
                            <div className="text-xs space-y-1.5 pt-1">
                              {dec.original_content && (
                                <div className="p-2 rounded bg-rose-950/20 border border-rose-900/30 text-[11px] text-rose-300 line-clamp-2">
                                  <span className="text-slate-400 block font-mono text-[10px] uppercase">Prior Version:</span>
                                  "{dec.original_content}"
                                </div>
                              )}
                              <div className="p-2 rounded bg-emerald-950/20 border border-emerald-900/30 text-[11px] text-emerald-300 line-clamp-2">
                                <span className="text-slate-400 block font-mono text-[10px] uppercase">New / Corrected Version:</span>
                                "{dec.edited_content}"
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end shrink-0">
              <button
                onClick={() => setHistoryModalItem(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
