import React from 'react';
import { 
  LayoutDashboard, 
  Sparkles, 
  FolderKanban, 
  ShieldCheck, 
  FileText, 
  BrainCircuit, 
  Settings, 
  HelpCircle
} from 'lucide-react';
import { NexoraLogo } from '../common/NexoraLogo';
import { LinkedinIcon } from '../common/BrandIcons';
import type { HealthCheckResponse } from '../../types';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: any) => void;
  pendingReviewCount: number;
  health: HealthCheckResponse | null;
  onOpenAuditLog?: () => void;
  onOpenLinkedInModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  pendingReviewCount,
  onOpenAuditLog,
  onOpenLinkedInModal
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null, badgeColor: '' },
    { id: 'studio', label: 'Create Content', icon: Sparkles, badge: null, badgeColor: '' },
    { id: 'library', label: 'Content Library', icon: FolderKanban, badge: null, badgeColor: '' },
    { 
      id: 'review', 
      label: 'Review Queue', 
      icon: ShieldCheck, 
      badge: pendingReviewCount > 0 ? pendingReviewCount : null,
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/40' 
    },
    { id: 'publishing', label: 'LinkedIn Publishing', icon: LinkedinIcon, badge: 'LIVE', badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-500/40' },
    { id: 'audit', label: 'Audit Log', icon: FileText, badge: null, badgeColor: '' },
    { id: 'learning', label: 'Feedback Memory', icon: BrainCircuit, badge: null, badgeColor: '' },
  ];

  return (
    <aside className="w-64 bg-[#0A101D] border-r border-slate-800/80 flex flex-col justify-between shrink-0 h-screen sticky top-0 z-40 select-none text-slate-300">
      {/* Top Branding & Workspace */}
      <div>
        <div className="p-5 border-b border-slate-800/80">
          <NexoraLogo size="md" showTagline={true} />
        </div>

        {/* Active Customer Workspace Selector */}
        <div className="px-4 py-3 bg-slate-900/60 border-b border-slate-800/60">
          <div className="flex items-center justify-between p-2 rounded-xl bg-slate-800/40 border border-slate-700/50 hover:border-slate-600 transition-all cursor-pointer">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-600 to-teal-500 flex items-center justify-center font-bold text-white text-xs shrink-0 shadow-sm">
                JA
              </div>
              <div className="overflow-hidden">
                <p className="text-xs font-bold text-white tracking-wide truncate">JA Assure</p>
                <p className="text-[10px] text-slate-400 font-mono">Workspace</p>
              </div>
            </div>
            <span className="w-2 h-2 rounded-full bg-emerald-400" title="Connected" />
          </div>
        </div>

        {/* Primary Navigation Menu */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  if (item.id === 'audit' && onOpenAuditLog) {
                    onOpenAuditLog();
                  } else {
                    setActiveTab(item.id);
                  }
                }}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-medium transition-all cursor-pointer group ${
                  isActive 
                    ? 'bg-blue-600/15 text-blue-300 border border-blue-500/30 font-semibold shadow-sm' 
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 transition-colors ${
                    isActive ? 'text-blue-400' : 'text-slate-400 group-hover:text-slate-200'
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

      {/* Footer Area — Connected LinkedIn Profile & Help */}
      <div className="p-4 border-t border-slate-800/80 bg-[#070C16] space-y-3">
        {/* Connected LinkedIn Profile Card */}
        <div 
          onClick={onOpenLinkedInModal}
          className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-blue-500/40 transition-all cursor-pointer space-y-1.5"
        >
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-300 font-semibold flex items-center gap-1.5">
              <LinkedinIcon className="w-3.5 h-3.5 text-[#0077B5]" />
              Madhan D
            </span>
            <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              CONNECTED
            </span>
          </div>
          <p className="text-[10px] text-slate-400 truncate">
            Personal LinkedIn Profile
          </p>
        </div>

        {/* Bottom Utility Links */}
        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1 pt-1">
          <button className="flex items-center gap-1 hover:text-slate-200 cursor-pointer">
            <Settings className="w-3.5 h-3.5" />
            Settings
          </button>
          <button className="flex items-center gap-1 hover:text-slate-200 cursor-pointer">
            <HelpCircle className="w-3.5 h-3.5" />
            Help
          </button>
        </div>
      </div>
    </aside>
  );
};
