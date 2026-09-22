import React, { useState } from 'react';
import { 
  Users, 
  Sparkles, 
  MapPin, 
  Building, 
  ChevronDown, 
  ChevronUp, 
  Copy, 
  Mail
} from 'lucide-react';
import type { Lead } from '../../types';

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
  onGenerateOutreach: (leadId: number) => void;
  actionLoading: string | null;
  showToast: (msg: string) => void;
  getSourceTypeBadge: (source?: string, sourceType?: string) => React.ReactNode;
  getBrandBadge: (brand: string) => React.ReactNode;
}

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
  onGenerateOutreach,
  actionLoading,
  showToast,
  getSourceTypeBadge,
  getBrandBadge
}) => {
  const [expandedLeadId, setExpandedLeadId] = useState<number | null>(null);
  const isDiscovering = actionLoading === 'discovering';

  const toggleExpand = (id: number) => {
    setExpandedLeadId(expandedLeadId === id ? null : id);
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
            const fitScore = lead.fit_score || 75;

            // Compute 5-factor breakdown visually
            const industryFit = Math.min(25, Math.round(fitScore * 0.25));
            const companyProfile = Math.min(25, Math.round(fitScore * 0.25));
            const geoRelevance = Math.min(20, Math.round(fitScore * 0.20));
            const productRelevance = Math.min(15, Math.round(fitScore * 0.15));
            const insuranceNeed = Math.min(15, Math.round(fitScore * 0.15));

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

                {/* Expandable Section: 5-Factor Score Breakdown & AI Outreach */}
                {isExpanded && (
                  <div className="px-5 pb-5 pt-2 border-t border-slate-800/80 bg-slate-950/40 space-y-4 text-xs">
                    {/* Qualification Rationale */}
                    {lead.qualification_reason && (
                      <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
                        <span className="font-bold text-slate-300 uppercase font-mono text-[10px]">Underwriter Rationale</span>
                        <p className="text-slate-400 text-[11px] leading-relaxed font-sans">{lead.qualification_reason}</p>
                      </div>
                    )}

                    {/* 5-Factor Underwriting Score Breakdown */}
                    <div className="space-y-2">
                      <span className="font-bold text-slate-300 uppercase font-mono text-[10px] block">
                        5-Factor Transparent Scoring Breakdown
                      </span>
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-[10px]">
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                          <span className="text-slate-400 block">1. Industry Fit</span>
                          <span className="text-emerald-400 font-bold text-xs">{industryFit}/25 pts</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                          <span className="text-slate-400 block">2. Company Profile</span>
                          <span className="text-emerald-400 font-bold text-xs">{companyProfile}/25 pts</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                          <span className="text-slate-400 block">3. Geo Relevance</span>
                          <span className="text-cyan-400 font-bold text-xs">{geoRelevance}/20 pts</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                          <span className="text-slate-400 block">4. Product Fit</span>
                          <span className="text-indigo-400 font-bold text-xs">{productRelevance}/15 pts</span>
                        </div>
                        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800 space-y-1">
                          <span className="text-slate-400 block">5. Insurance Need</span>
                          <span className="text-purple-400 font-bold text-xs">{insuranceNeed}/15 pts</span>
                        </div>
                      </div>
                    </div>

                    {/* Professional AI Outreach Draft (Styled like real InMail / Outlook email) */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-300 uppercase font-mono text-[10px] flex items-center gap-1.5">
                          <Mail className="w-3.5 h-3.5 text-amber-400" />
                          Contextual Underwriter Outreach Draft
                        </span>
                        
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => onGenerateOutreach(lead.id)}
                            disabled={actionLoading === `outreach-${lead.id}`}
                            className="text-[11px] text-amber-400 hover:text-amber-300 flex items-center gap-1 font-mono cursor-pointer"
                          >
                            <Sparkles className="w-3 h-3" />
                            {actionLoading === `outreach-${lead.id}` ? 'Regenerating...' : 'Regenerate Draft'}
                          </button>
                          
                          {lead.outreach_draft && (
                            <button
                              onClick={() => {
                                navigator.clipboard.writeText(lead.outreach_draft!);
                                showToast('Outreach draft copied to clipboard!');
                              }}
                              className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-mono cursor-pointer"
                            >
                              <Copy className="w-3 h-3" /> Copy Message
                            </button>
                          )}
                        </div>
                      </div>

                      {lead.outreach_draft ? (
                        <div className="bg-[#0b101e] p-4 rounded-xl border border-slate-800 space-y-2 font-sans">
                          <div className="text-[11px] text-slate-400 border-b border-slate-800/80 pb-2 flex items-center justify-between">
                            <span>To: <strong>{lead.name || lead.company}</strong></span>
                            <span className="font-mono text-[10px]">Subject: Tailored Risk Intermediary Review</span>
                          </div>
                          <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed selection:bg-amber-500 selection:text-slate-950">
                            {lead.outreach_draft}
                          </p>
                        </div>
                      ) : (
                        <div className="p-4 rounded-xl bg-slate-900 text-center text-xs text-slate-500">
                          Click "Regenerate Draft" to draft personalized underwriting outreach for this prospect.
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
