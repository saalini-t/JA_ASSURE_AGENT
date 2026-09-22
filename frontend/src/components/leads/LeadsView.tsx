import React, { useState } from 'react';
import {
  Users,
  Sparkles,
  MapPin,
  Building,
  ChevronDown,
  ChevronUp,
  Copy,
  Mail,
  CheckCircle2,
  XCircle,
  Send,
  Pencil,
  ShieldAlert
} from 'lucide-react';
import type { Lead, LeadOutreach } from '../../types';
import { api } from '../../services/api';

interface LeadsViewProps {
  leads: Lead[];
  leadCountry: string;
  setLeadCountry: (country: string) => void;
  leadBrand: string;
  setLeadBrand: (brand: string) => void;
  leadIndustry: string;
  setLeadIndustry: (industry: string) => void;
  onDiscoverLeads: () => void;
  onOpenEnrichModal: (lead: Lead) => void;
  actionLoading: string | null;
  showToast: (msg: string) => void;
  getSourceTypeBadge: (source?: string, sourceType?: string) => React.ReactNode;
  getBrandBadge: (brand: string) => React.ReactNode;
}

const complianceBadge = (status: string) => {
  const s = (status || '').toLowerCase();
  if (s === 'passed') return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Compliance: Passed</span>;
  if (s === 'flagged' || s === 'failed') return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30">Compliance: {status}</span>;
  return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">Compliance: {status || 'pending'}</span>;
};

const statusBadge = (status: string) => {
  const s = (status || '').toLowerCase();
  if (s === 'approved') return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Approved</span>;
  if (s === 'rejected') return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30">Rejected</span>;
  if (s === 'human_review') return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">Awaiting Review</span>;
  return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">{status || 'pending'}</span>;
};

const sendStatusBadge = (sendStatus: string) => {
  const s = (sendStatus || '').toLowerCase();
  if (s === 'sent') return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/15 text-blue-300 border border-blue-500/30 flex items-center gap-1"><Send className="w-3 h-3" /> Sent</span>;
  if (s === 'failed') return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30">Send Failed</span>;
  return <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">Draft</span>;
};

export const LeadsView: React.FC<LeadsViewProps> = ({
  leads,
  leadCountry,
  setLeadCountry,
  leadBrand,
  setLeadBrand,
  leadIndustry,
  setLeadIndustry,
  onDiscoverLeads,
  onOpenEnrichModal,
  actionLoading,
  showToast,
  getSourceTypeBadge,
  getBrandBadge
}) => {
  const [expandedLeadId, setExpandedLeadId] = useState<number | null>(null);
  const [outreachByLead, setOutreachByLead] = useState<Record<number, LeadOutreach[]>>({});
  const [outreachBusy, setOutreachBusy] = useState<string | null>(null); // e.g. "generate-3", "approve-7"
  const [editingOutreachId, setEditingOutreachId] = useState<number | null>(null);
  const [editBody, setEditBody] = useState<string>('');
  const isDiscovering = actionLoading === 'discovering';

  const refreshOutreach = async (leadId: number) => {
    const list = await api.getLeadOutreachList(leadId);
    setOutreachByLead((prev) => ({ ...prev, [leadId]: list }));
    return list;
  };

  const toggleExpand = async (id: number) => {
    if (expandedLeadId === id) {
      setExpandedLeadId(null);
      return;
    }
    setExpandedLeadId(id);
    if (!outreachByLead[id]) {
      try {
        await refreshOutreach(id);
      } catch (err: any) {
        showToast(`Failed to load outreach history: ${err.message}`);
      }
    }
  };

  const handleGenerate = async (leadId: number) => {
    setOutreachBusy(`generate-${leadId}`);
    try {
      await api.generateStructuredOutreach(leadId);
      await refreshOutreach(leadId);
      showToast('✓ Structured, compliance-checked outreach draft generated — awaiting human review.');
    } catch (err: any) {
      showToast(`Outreach generation failed: ${err.message}`);
    } finally {
      setOutreachBusy(null);
    }
  };

  const handleApprove = async (leadId: number, outreachId: number) => {
    setOutreachBusy(`approve-${outreachId}`);
    try {
      await api.approveOutreach(outreachId);
      await refreshOutreach(leadId);
      showToast('✓ Outreach approved. It may now be sent.');
    } catch (err: any) {
      showToast(`Approval failed: ${err.message}`);
    } finally {
      setOutreachBusy(null);
    }
  };

  const handleReject = async (leadId: number, outreachId: number) => {
    const notes = window.prompt('Rejection notes (required):', 'Tone/claims need revision');
    if (notes === null) return;
    setOutreachBusy(`reject-${outreachId}`);
    try {
      await api.rejectOutreach(outreachId, 'human_edit', notes || 'Rejected by reviewer');
      await refreshOutreach(leadId);
      showToast('✕ Outreach rejected.');
    } catch (err: any) {
      showToast(`Rejection failed: ${err.message}`);
    } finally {
      setOutreachBusy(null);
    }
  };

  const startEdit = (outreach: LeadOutreach) => {
    setEditingOutreachId(outreach.id);
    setEditBody(outreach.body);
  };

  const handleSaveEdit = async (leadId: number) => {
    if (editingOutreachId === null) return;
    setOutreachBusy(`edit-${editingOutreachId}`);
    try {
      await api.editOutreach(editingOutreachId, editBody);
      await refreshOutreach(leadId);
      setEditingOutreachId(null);
      showToast('✓ Outreach edited and re-submitted for human review (compliance re-checked).');
    } catch (err: any) {
      showToast(`Edit failed: ${err.message}`);
    } finally {
      setOutreachBusy(null);
    }
  };

  const handleSend = async (leadId: number, outreachId: number) => {
    setOutreachBusy(`send-${outreachId}`);
    try {
      const updated = await api.sendOutreach(outreachId);
      await refreshOutreach(leadId);
      if (updated.send_status === 'sent') {
        showToast('✓ Outreach email sent.');
      } else {
        showToast(`Send failed: ${updated.send_error || 'unknown error'}`);
      }
    } catch (err: any) {
      showToast(`Send failed: ${err.message}`);
    } finally {
      setOutreachBusy(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Lead Intelligence Command Header & Discovery Filters */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <Users className="w-4 h-4 text-indigo-400" />
              B2B Lead Intelligence & Risk Underwriting Match
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              5-factor underwriting qualification algorithm scoring high-value prospects across Southeast Asia
            </p>
          </div>
          <span className="text-[10px] font-mono text-indigo-300 bg-indigo-500/10 border border-indigo-500/30 px-2.5 py-1 rounded-full w-fit">
            5-Factor Scoring Active
          </span>
        </div>

        {/* Discovery Filter Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="text-slate-300 font-medium block">Brand Persona</label>
            <select
              value={leadBrand}
              onChange={(e) => setLeadBrand(e.target.value)}
              className="w-full mt-1.5 bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200 focus:ring-1 focus:ring-indigo-500"
            >
              <option value="all">All Brand Lines</option>
              <option value="jade">Jade (Luxury Jewellery)</option>
              <option value="doctorshield">DoctorShield (Med Indemnity)</option>
              <option value="jaguartransit">Jaguar Transit (Cargo)</option>
            </select>
          </div>

          <div>
            <label className="text-slate-300 font-medium block">Jurisdiction / Country</label>
            <select
              value={leadCountry}
              onChange={(e) => setLeadCountry(e.target.value)}
              className="w-full mt-1.5 bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200 focus:ring-1 focus:ring-indigo-500"
            >
              <option value="all">All Jurisdictions</option>
              <option value="Singapore">Singapore (MAS Licensed)</option>
              <option value="Malaysia">Malaysia (BNM Regulated)</option>
              <option value="Indonesia">Indonesia (OJK Compliance)</option>
              <option value="Thailand">Thailand (OIC Regulated)</option>
            </select>
          </div>

          <div>
            <label className="text-slate-300 font-medium block">Target Vertical</label>
            <input
              type="text"
              value={leadIndustry}
              onChange={(e) => setLeadIndustry(e.target.value)}
              placeholder="e.g. Diamond Dealer, Clinic"
              className="w-full mt-1.5 bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200 focus:ring-1 focus:ring-indigo-500"
            >
            </input>
          </div>

          <div className="flex items-end">
            <button
              onClick={onDiscoverLeads}
              disabled={isDiscovering}
              className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              {isDiscovering ? 'Discovering Prospects...' : 'Discover & Score Leads'}
            </button>
          </div>
        </div>
      </div>

      {/* Prospect Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Building className="w-4 h-4 text-indigo-400" />
            Qualified Prospects ({leads.length})
          </h3>
          <span className="text-[11px] font-mono text-slate-400">
            Sorted by Underwriting Fit Score
          </span>
        </div>

        {leads.length === 0 ? (
          <div className="glass-panel p-16 rounded-2xl border border-slate-800 text-center space-y-2">
            <Users className="w-8 h-8 text-slate-600 mx-auto" />
            <h4 className="text-sm font-semibold text-slate-200">No leads match the current filters</h4>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              Use the discovery controls above to scan for high-net-worth jewelers, aesthetic surgeons, or transit operators.
            </p>
          </div>
        ) : (
          leads.map((lead) => {
            const isExpanded = expandedLeadId === lead.id;
            const fitScore = lead.fit_score || 0;
            const breakdown = lead.scoring_breakdown;
            const outreachList = outreachByLead[lead.id] || [];
            const latestOutreach = outreachList.length > 0 ? outreachList[outreachList.length - 1] : null;

            return (
              <div
                key={lead.id}
                className="glass-panel rounded-2xl border border-slate-800 hover:border-slate-700 transition-all overflow-hidden"
              >
                {/* Main Card Row */}
                <div className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1.5 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-bold text-sm text-slate-100">{lead.company}</h4>
                      {lead.recommended_brand && getBrandBadge(lead.recommended_brand)}
                      {getSourceTypeBadge(lead.source, lead.source_type)}
                      <span className="text-[10px] font-mono text-slate-500">#{lead.id}</span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400 flex-wrap">
                      <span className="flex items-center gap-1">
                        <Building className="w-3.5 h-3.5 text-slate-500" />
                        {lead.industry}
                      </span>
                      {lead.location && (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5 text-slate-500" />
                          {lead.location}
                        </span>
                      )}
                      {lead.name && (
                        <span className="text-slate-300 font-medium">
                          Contact: {lead.name}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right side: Score badge & Action Buttons */}
                  <div className="flex items-center gap-3 shrink-0 self-end md:self-center">
                    <div className="text-right">
                      <div className="text-[10px] font-mono text-slate-400 uppercase">Underwriting Fit</div>
                      <span className={`text-base font-bold font-mono px-3 py-0.5 rounded-full inline-block ${
                        fitScore >= 80 ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                        fitScore >= 60 ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' :
                        'bg-slate-800 text-slate-400 border border-slate-700'
                      }`}>
                        {fitScore}%
                      </span>
                    </div>

                    <button
                      onClick={() => onOpenEnrichModal(lead)}
                      className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/40 flex items-center gap-1 transition-colors cursor-pointer"
                    >
                      <Sparkles className="w-3.5 h-3.5" /> Enrich
                    </button>

                    <button
                      onClick={() => toggleExpand(lead.id)}
                      className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 cursor-pointer transition-colors"
                      title="Toggle 5-Factor Score & Outreach"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Expandable Section: 5-Factor Score Breakdown & Governed Outreach */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-slate-800/80 bg-slate-950/40 space-y-4 text-xs">
                    {/* Qualification Rationale */}
                    {lead.qualification_reason && (
                      <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                        <span className="font-bold text-slate-300 uppercase font-mono text-[10px]">Underwriter Rationale</span>
                        <p className="text-slate-400 text-[11px] leading-relaxed font-sans">{lead.qualification_reason}</p>
                      </div>
                    )}

                    {/* 5-Factor Underwriting Score Breakdown -- real backend values only */}
                    <div className="space-y-2">
                      <span className="font-bold text-slate-300 uppercase font-mono text-[10px] block">
                        5-Factor Transparent Scoring Breakdown
                      </span>
                      {breakdown ? (
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-[10px]">
                          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1" title={breakdown.industry_fit_reason}>
                            <span className="text-slate-400 block">1. Industry Fit</span>
                            <span className="text-emerald-400 font-bold text-xs">{breakdown.industry_fit}/25 pts</span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1" title={breakdown.company_profile_reason}>
                            <span className="text-slate-400 block">2. Company Profile</span>
                            <span className="text-emerald-400 font-bold text-xs">{breakdown.company_profile}/20 pts</span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1" title={breakdown.geographic_relevance_reason}>
                            <span className="text-slate-400 block">3. Geo Relevance</span>
                            <span className="text-cyan-400 font-bold text-xs">{breakdown.geographic_relevance}/20 pts</span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1" title={breakdown.product_relevance_reason}>
                            <span className="text-slate-400 block">4. Product Fit</span>
                            <span className="text-indigo-400 font-bold text-xs">{breakdown.product_relevance}/20 pts</span>
                          </div>
                          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1" title={breakdown.potential_insurance_need_reason}>
                            <span className="text-slate-400 block">5. Insurance Need</span>
                            <span className="text-purple-400 font-bold text-xs">{breakdown.potential_insurance_need}/15 pts</span>
                          </div>
                        </div>
                      ) : (
                        <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-slate-500 flex items-center gap-2">
                          <ShieldAlert className="w-3.5 h-3.5" />
                          No stored scoring breakdown for this lead yet — run "Enrich" to compute and record one.
                        </div>
                      )}
                    </div>

                    {/* Governed Outreach: generate -> compliance -> human review -> approve/reject/edit -> send */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-300 uppercase font-mono text-[10px] flex items-center gap-1.5">
                          <Mail className="w-3.5 h-3.5 text-amber-400" />
                          Governed Underwriter Outreach
                        </span>
                        <button
                          onClick={() => handleGenerate(lead.id)}
                          disabled={outreachBusy === `generate-${lead.id}`}
                          className="text-[11px] text-amber-400 hover:text-amber-300 flex items-center gap-1 font-mono cursor-pointer disabled:opacity-50"
                        >
                          <Sparkles className="w-3 h-3" />
                          {outreachBusy === `generate-${lead.id}` ? 'Generating...' : 'Generate New Draft'}
                        </button>
                      </div>

                      {latestOutreach ? (
                        <div className="bg-[#0b101e] p-4 rounded-xl border border-slate-800 space-y-3 font-sans">
                          <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-800/80 pb-2">
                            <span className="text-[11px] text-slate-400">
                              To: <strong>{lead.name || lead.company}</strong> {lead.email ? `<${lead.email}>` : <em className="text-slate-600">(no verified email on file)</em>}
                            </span>
                            <div className="flex items-center gap-1.5">
                              {statusBadge(latestOutreach.status)}
                              {complianceBadge(latestOutreach.compliance_status)}
                              {sendStatusBadge(latestOutreach.send_status)}
                            </div>
                          </div>

                          <p className="text-[11px] font-mono text-slate-500">Subject: {latestOutreach.subject}</p>

                          {editingOutreachId === latestOutreach.id ? (
                            <div className="space-y-2">
                              <textarea
                                value={editBody}
                                onChange={(e) => setEditBody(e.target.value)}
                                rows={6}
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:ring-1 focus:ring-amber-500"
                              />
                              <div className="flex gap-2">
                                <button
                                  onClick={() => handleSaveEdit(lead.id)}
                                  disabled={outreachBusy === `edit-${latestOutreach.id}`}
                                  className="px-3 py-1 rounded-lg bg-amber-600/30 hover:bg-amber-600/50 text-amber-300 border border-amber-500/40 text-[11px] font-semibold cursor-pointer"
                                >
                                  Save & Resubmit for Review
                                </button>
                                <button
                                  onClick={() => setEditingOutreachId(null)}
                                  className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] cursor-pointer"
                                >
                                  Cancel
                                </button>
                              </div>
                            </div>
                          ) : (
                            <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed selection:bg-amber-500 selection:text-slate-950">
                              {latestOutreach.body}
                            </p>
                          )}

                          {latestOutreach.personalization_points.length > 0 && (
                            <div className="text-[10px] text-slate-500 font-mono">
                              Personalization: {latestOutreach.personalization_points.join(' • ')}
                            </div>
                          )}

                          {latestOutreach.send_error && (
                            <p className="text-[11px] text-rose-400 font-mono">Send error: {latestOutreach.send_error}</p>
                          )}

                          {/* HITL actions -- gated exactly as the backend gates them */}
                          <div className="flex flex-wrap gap-2 pt-1">
                            <button
                              onClick={() => navigator.clipboard.writeText(latestOutreach.body).then(() => showToast('Copied to clipboard.'))}
                              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] flex items-center gap-1 cursor-pointer"
                            >
                              <Copy className="w-3 h-3" /> Copy
                            </button>

                            {latestOutreach.status === 'human_review' && (
                              <>
                                <button
                                  onClick={() => handleApprove(lead.id, latestOutreach.id)}
                                  disabled={outreachBusy === `approve-${latestOutreach.id}`}
                                  className="px-2.5 py-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/40 text-emerald-300 border border-emerald-500/40 text-[11px] flex items-center gap-1 cursor-pointer disabled:opacity-50"
                                >
                                  <CheckCircle2 className="w-3 h-3" /> Approve
                                </button>
                                <button
                                  onClick={() => startEdit(latestOutreach)}
                                  className="px-2.5 py-1 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/40 text-[11px] flex items-center gap-1 cursor-pointer"
                                >
                                  <Pencil className="w-3 h-3" /> Edit
                                </button>
                                <button
                                  onClick={() => handleReject(lead.id, latestOutreach.id)}
                                  disabled={outreachBusy === `reject-${latestOutreach.id}`}
                                  className="px-2.5 py-1 rounded-lg bg-rose-600/20 hover:bg-rose-600/40 text-rose-300 border border-rose-500/40 text-[11px] flex items-center gap-1 cursor-pointer disabled:opacity-50"
                                >
                                  <XCircle className="w-3 h-3" /> Reject
                                </button>
                              </>
                            )}

                            {latestOutreach.status === 'approved' && latestOutreach.send_status !== 'sent' && (
                              <button
                                onClick={() => handleSend(lead.id, latestOutreach.id)}
                                disabled={outreachBusy === `send-${latestOutreach.id}` || !lead.email}
                                title={!lead.email ? 'No verified email on file -- nothing real to send to' : undefined}
                                className="px-2.5 py-1 rounded-lg bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 border border-blue-500/40 text-[11px] flex items-center gap-1 cursor-pointer disabled:opacity-50"
                              >
                                <Send className="w-3 h-3" /> {outreachBusy === `send-${latestOutreach.id}` ? 'Sending...' : 'Send Email'}
                              </button>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="p-4 rounded-xl bg-slate-900 text-center text-xs text-slate-500">
                          No outreach draft yet. Click "Generate New Draft" to create a compliance-checked draft for human review.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
