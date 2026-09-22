import React from 'react';
import { 
  FileText, 
  Clock, 
  CheckCircle2, 
  Plus, 
  Sparkles, 
  ArrowRight, 
  ShieldCheck, 
  ExternalLink
} from 'lucide-react';
import { LinkedinIcon } from '../common/BrandIcons';
import { WorkflowArchitectureBanner } from '../common/WorkflowArchitectureBanner';
import type { DashboardSummary, ContentQueueItem } from '../../types';
import { API_ORIGIN } from '../../services/api';

interface DashboardViewProps {
  summary: DashboardSummary | null;
  queue: ContentQueueItem[];
  onNavigate: (tab: string) => void;
  onOpenLinkedInModal: () => void;
  onOpenAutonomousModal: () => void;
  onOpenAuditLog: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  summary,
  queue,
  onNavigate,
  onOpenLinkedInModal,
  onOpenAutonomousModal,
  onOpenAuditLog
}) => {
  const publishedCount = summary?.published ?? 0;
  const pendingCount = summary?.pending_human_review ?? 0;
  const totalCount = summary?.total_content ?? 0;

  const recentItems = queue.slice(0, 5);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-300">
      
      {/* Welcome Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Nexora Intelligence Console</h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time autonomous AI marketing and compliant asset publishing for JA Assure.
          </p>
        </div>

        {/* 1-Click Autonomous Action */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenAutonomousModal}
            className="px-5 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-teal-500 hover:opacity-95 text-white transition-all flex items-center gap-2 shadow-lg shadow-blue-500/20 cursor-pointer"
          >
            <Sparkles className="w-4 h-4" />
            Run Autonomous Campaign
          </button>
        </div>
      </div>

      {/* 4 Top KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        
        {/* Card 1: Total Content */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-2xl p-5 space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Total Content Assets</span>
            <FileText className="w-4 h-4 text-slate-500" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-white font-mono">{totalCount}</span>
            <span className="text-[11px] text-slate-400 font-semibold font-mono">in database</span>
          </div>
        </div>

        {/* Card 2: Pending Review */}
        <div 
          onClick={() => onNavigate('review')}
          className="bg-[#0F172A] border border-amber-500/30 hover:border-amber-500/60 transition-all rounded-2xl p-5 space-y-2 shadow-lg cursor-pointer"
        >
          <div className="flex items-center justify-between text-xs text-amber-300/80">
            <span>Review Queue</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-amber-300 font-mono">{pendingCount}</span>
            <span className="text-[11px] text-amber-400/90 font-semibold font-mono">
              {pendingCount > 0 ? 'Needs approval' : 'Queue cleared'}
            </span>
          </div>
        </div>

        {/* Card 3: Published */}
        <div className="bg-[#0F172A] border border-emerald-500/30 rounded-2xl p-5 space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-xs text-emerald-300/80">
            <span>Live Published</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-300 font-mono">{publishedCount}</span>
            <span className="text-[11px] text-emerald-400 font-semibold font-mono">LinkedIn Live</span>
          </div>
        </div>

        {/* Card 4: LinkedIn Connected */}
        <div 
          onClick={onOpenLinkedInModal}
          className="bg-[#0F172A] border border-blue-500/30 hover:border-blue-500/60 transition-all rounded-2xl p-5 space-y-2 shadow-lg cursor-pointer"
        >
          <div className="flex items-center justify-between text-xs text-blue-300/80">
            <span>LinkedIn Identity</span>
            <LinkedinIcon className="w-4 h-4 text-[#0077B5]" />
          </div>
          <div className="space-y-0.5">
            <span className="text-lg font-bold text-white block">Madhan D</span>
            <span className="text-[10px] text-emerald-400 font-mono font-semibold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> Authorized & Live
            </span>
          </div>
        </div>

      </div>

      {/* Interactive Autonomous Workflow Architecture Banner */}
      <WorkflowArchitectureBanner onNavigate={onNavigate} />

      {/* Main Grid: Recent Content (Left) & Quick Actions (Right) matching Screen 3 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left 2 Cols: Recent Content */}
        <div className="lg:col-span-2 bg-[#0F172A] border border-slate-800 rounded-2xl p-6 space-y-5 shadow-xl">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-white text-base">Recent Content</h3>
            <button 
              onClick={() => onNavigate('library')}
              className="text-xs font-semibold text-blue-400 hover:text-blue-300 flex items-center gap-1 cursor-pointer"
            >
              View all <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            {recentItems.length > 0 ? (
              recentItems.map((item) => {
                const isPub = item.status === 'published';
                const isApp = item.status === 'approved';
                return (
                  <div 
                    key={item.id}
                    className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/90 hover:border-slate-700 transition-all flex items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-3.5 overflow-hidden">
                      <div className="w-9 h-9 rounded-lg bg-[#0077B5]/15 border border-[#0077B5]/30 flex items-center justify-center text-[#0077B5] shrink-0 mt-0.5">
                        <LinkedinIcon className="w-4 h-4 fill-current" />
                      </div>
                      <div className="overflow-hidden space-y-1">
                        <p className="text-xs font-semibold text-white truncate max-w-[420px]">
                          {item.topic || 'Specialised insurance considerations for bespoke collections'}
                        </p>
                        <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                          <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 uppercase font-bold">
                            {item.brand}
                          </span>
                          <span>•</span>
                          <span>{item.platform.toUpperCase()}</span>
                          <span>•</span>
                          <span>Score: {item.compliance_score || 100}/100</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-mono font-bold border ${
                        isPub 
                          ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' 
                          : isApp 
                          ? 'bg-blue-500/15 text-blue-300 border-blue-500/30'
                          : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                      }`}>
                        {item.status.toUpperCase()}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-10 text-slate-400 text-xs">
                No recent content. Click "Create New Content" to start!
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Col: Quick Actions matching Screen 3 */}
        <div className="space-y-4">
          <div className="bg-[#0F172A] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <h3 className="font-bold text-white text-base">Quick Actions</h3>

            <div className="space-y-2.5">
              <button
                onClick={() => onNavigate('studio')}
                className="w-full p-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-between transition-colors shadow-lg shadow-blue-600/20 cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <Plus className="w-4 h-4" />
                  <span>Create New Content</span>
                </div>
                <ArrowRight className="w-4 h-4 opacity-80" />
              </button>

              <button
                onClick={() => onNavigate('review')}
                className="w-full p-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold text-xs flex items-center justify-between transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ShieldCheck className="w-4 h-4 text-amber-400" />
                  <span>View Review Queue</span>
                </div>
                <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300">
                  {pendingCount}
                </span>
              </button>

              <button
                onClick={onOpenLinkedInModal}
                className="w-full p-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold text-xs flex items-center justify-between transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <LinkedinIcon className="w-4 h-4 text-[#0077B5]" />
                  <span>Manage LinkedIn Connection</span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 font-bold">ACTIVE</span>
              </button>

              <button
                onClick={onOpenAuditLog}
                className="w-full p-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold text-xs flex items-center justify-between transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <FileText className="w-4 h-4 text-slate-400" />
                  <span>View Audit Log Timeline</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
              </button>

              <a
                href={`${API_ORIGIN}/evidence/Nexora_JA_Assure_Autonomous_Execution_Evidence_Report.pdf`}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full p-3 rounded-xl bg-teal-950/30 hover:bg-teal-950/50 text-teal-300 border border-teal-500/40 font-semibold text-xs flex items-center justify-between transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-2.5">
                  <ExternalLink className="w-4 h-4 text-teal-400" />
                  <span>Open HD Evidence PDF</span>
                </div>
                <span className="text-[10px] font-mono font-bold bg-teal-500/20 px-2 py-0.5 rounded text-teal-300">PDF</span>
              </a>
            </div>
          </div>

          {/* Connected Identity Info Card */}
          <div className="p-4 rounded-2xl bg-gradient-to-br from-blue-950/20 via-slate-900 to-slate-950 border border-blue-900/40 text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 font-mono text-[10px]">CURRENT PUBLISHER</span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-blue-500/20 text-blue-300 font-bold">LINKEDIN</span>
            </div>
            <p className="font-bold text-white">Madhan D</p>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Posts will be published live to personal LinkedIn profile.
            </p>
          </div>
        </div>

      </div>

    </div>
  );
};
