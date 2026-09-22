import React from 'react';
import { RefreshCw, Sliders, ShieldCheck } from 'lucide-react';
import type { HealthCheckResponse } from '../../types';

interface HeaderProps {
  activeTab: 'dashboard' | 'studio' | 'review' | 'competitors' | 'leads' | 'learning' | 'analytics';
  selectedBrand: string;
  setSelectedBrand: (brand: string) => void;
  health: HealthCheckResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

const tabMeta: Record<string, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'AI Marketing Command Center',
    subtitle: 'Research, generate, comply, review and learn — in one controlled multi-brand workflow.'
  },
  studio: {
    title: 'Multi-Brand Content Studio',
    subtitle: 'Persona-aligned generation with automated statutory compliance and persistent lesson injection.'
  },
  review: {
    title: 'Human Governance & Review Center',
    subtitle: 'Mandatory human sign-off gate before publishing dispatch. Editorial feedback continuously trains AI memory.'
  },
  competitors: {
    title: 'Market Intelligence & Whitespace',
    subtitle: 'Source-backed competitor tracking, positioning analysis, and counter-messaging opportunities.'
  },
  leads: {
    title: 'B2B Lead Intelligence & Prospecting',
    subtitle: '5-factor underwriting qualification scoring with tailored AI-assisted risk outreach.'
  },
  learning: {
    title: 'Closed-Loop Learning Repository',
    subtitle: 'Autonomous memory synthesizing human rejections and edits into active prompt steering rules.'
  },
  analytics: {
    title: 'Operational Governance Analytics',
    subtitle: 'Live Supabase KPIs, regulatory pass rates, compliance health bands, and simulated dispatch activity.'
  }
};

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  selectedBrand,
  setSelectedBrand,
  health,
  loading,
  onRefresh
}) => {
  const current = tabMeta[activeTab] || tabMeta.dashboard;

  return (
    <header className="border-b border-slate-800/80 bg-[#0a0f1d]/90 backdrop-blur sticky top-0 z-30 px-6 py-3.5">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left: Workspace Title & Context */}
        <div className="space-y-0.5">
          <div className="flex items-center gap-2.5">
            <h1 className="text-base font-bold text-slate-100 tracking-tight">
              {current.title}
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              JA-ASSURE-OS
            </span>
          </div>
          <p className="text-xs text-slate-400 font-sans">
            {current.subtitle}
          </p>
        </div>

        {/* Right: Controls & Engine Status */}
        <div className="flex items-center gap-3 self-end md:self-auto shrink-0">
          {/* Brand Filter */}
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 shadow-sm">
            <Sliders className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[11px] font-mono text-slate-400 font-medium">Brand:</span>
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="bg-transparent text-xs text-slate-200 focus:outline-none cursor-pointer font-medium"
            >
              <option value="all" className="bg-[#0a0f1d] text-slate-200">All Brands (Portfolio)</option>
              <option value="jade" className="bg-[#0a0f1d] text-emerald-300">Jade (Luxury Jewellery)</option>
              <option value="doctorshield" className="bg-[#0a0f1d] text-blue-300">DoctorShield (Med Indemnity)</option>
              <option value="jaguartransit" className="bg-[#0a0f1d] text-amber-300">Jaguar Transit (High-Risk Cargo)</option>
            </select>
          </div>

          {/* Engine Health Pill */}
          <div className="hidden sm:flex items-center gap-2 text-xs px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 font-mono">
            <span className={`w-2 h-2 rounded-full ${health ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            <span className="text-slate-300 text-[11px]">
              {health?.llm_mode?.includes('live') ? 'Google Gemini 3.5 Flash' : 'Offline Safe'}
            </span>
          </div>

          {/* Compliance Safe Gate Pill */}
          <div className="hidden lg:flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>MAS Gate Active</span>
          </div>

          {/* Refresh Action */}
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors border border-slate-800 cursor-pointer disabled:opacity-50"
            title="Refresh All Database Signals"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-amber-400' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
};
