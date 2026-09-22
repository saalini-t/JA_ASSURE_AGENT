import React from 'react';
import { 
  TrendingUp, 
  Wand2, 
  ShieldCheck, 
  Search, 
  Users, 
  BrainCircuit, 
  Layers,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Send
} from 'lucide-react';
import type { HealthCheckResponse } from '../../types';

type TabId = 'dashboard' | 'studio' | 'review' | 'competitors' | 'leads' | 'publishing' | 'learning' | 'analytics';

interface SidebarProps {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  pendingReviewCount: number;
  health: HealthCheckResponse | null;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  pendingReviewCount,
  health
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Overview', icon: TrendingUp, badge: null },
    { id: 'studio', label: 'Content Studio', icon: Wand2, badge: null },
    { 
      id: 'review', 
      label: 'Review Center', 
      icon: ShieldCheck, 
      badge: pendingReviewCount > 0 ? pendingReviewCount : null,
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
    },
    { id: 'competitors', label: 'Competitor Intel', icon: Search, badge: null },
    { id: 'leads', label: 'Lead Intelligence', icon: Users, badge: null },
    { id: 'publishing', label: 'Publishing', icon: Send, badge: null },
    { id: 'learning', label: 'Closed-Loop Memory', icon: BrainCircuit, badge: null },
    { id: 'analytics', label: 'Governance Analytics', icon: Layers, badge: null },
  ] as const;

  return (
    <aside className="w-64 bg-[#0a0f1d] border-r border-slate-800/80 flex flex-col justify-between shrink-0 h-screen sticky top-0 z-40 select-none">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-slate-800/80 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/30 via-slate-800 to-slate-900 border border-amber-500/40 flex items-center justify-center shadow-lg shadow-amber-500/10 shrink-0">
            <span className="font-serif font-black text-amber-300 text-lg tracking-wider">JA</span>
          </div>
          <div className="overflow-hidden">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-sm tracking-widest text-slate-100 uppercase">JA Assure</span>
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
            </div>
            <p className="text-[10px] font-mono tracking-wider text-amber-400/80 font-medium uppercase truncate">
              Command Center
            </p>
          </div>
        </div>

        {/* Brand Tagline */}
        <div className="px-5 py-3 bg-slate-900/40 border-b border-slate-800/60">
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
            <span>MULTI-BRAND AI</span>
            <span className="text-emerald-400 font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> ONLINE
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all cursor-pointer group ${
                  isActive 
                    ? 'nav-item-active text-amber-200 font-semibold' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 transition-colors ${
                    isActive ? 'text-amber-400' : 'text-slate-500 group-hover:text-slate-300'
                  }`} />
                  <span>{item.label}</span>
                </div>

                {item.badge !== null && (
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold border ${item.badgeColor || 'bg-slate-800 text-slate-300 border-slate-700'}`}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Sidebar Footer — Operational & Engine Status */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/60 space-y-3">
        {/* Groq AI Status Card */}
        <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              AI Intelligence
            </span>
            <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
              health?.llm_mode?.includes('live') 
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
            }`}>
              {health?.llm_mode?.includes('live') ? 'GROQ LIVE' : 'OFFLINE MODE'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
            <span>Model Engine</span>
            <span className="text-slate-300">{health?.llm_model || 'llama-3.3-70b'}</span>
          </div>
        </div>

        {/* Regulatory & System Gate */}
        <div className="flex items-center justify-between px-1 text-[11px] text-slate-400 font-mono">
          <span className="flex items-center gap-1.5">
            {health?.database === 'connected' ? (
              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            ) : (
              <AlertTriangle className="w-3 h-3 text-rose-400" />
            )}
            MAS/MOH Gate
          </span>
          <span className="text-emerald-400 font-semibold">Active</span>
        </div>

        {/* Version */}
        <div className="text-[10px] font-mono text-slate-600 px-1 text-center">
          JA Assure Enterprise v2.4 • InsurTech
        </div>
      </div>
    </aside>
  );
};
