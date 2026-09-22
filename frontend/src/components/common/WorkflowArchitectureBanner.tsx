import React, { useState } from 'react';
import { 
  User, 
  Sparkles, 
  Layers, 
  Video, 
  ShieldCheck, 
  CheckCircle2, 
  Share2, 
  FileText, 
  Database, 
  RefreshCw, 
  ChevronRight,
  ArrowRight,
  Info,
  Check,
  Zap,
  RotateCcw
} from 'lucide-react';
import { LinkedinIcon } from './BrandIcons';

interface WorkflowArchitectureBannerProps {
  activeStage?: number; // 1 to 9
  onNavigate?: (tab: string) => void;
  compact?: boolean;
}

export const WorkflowArchitectureBanner: React.FC<WorkflowArchitectureBannerProps> = ({
  activeStage,
  onNavigate
}) => {
  const [selectedStep, setSelectedStep] = useState<number | null>(null);

  const workflowSteps = [
    {
      id: 1,
      title: 'User Input',
      badge: 'Web Dashboard',
      category: 'System / Business Logic',
      catColor: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
      icon: User,
      color: 'from-blue-600/20 to-indigo-600/20 text-blue-400 border-blue-500/30',
      items: ['Brand / Campaign', 'Topic / Goal', 'Platform (LinkedIn)', 'Format (Image / Video)', 'Additional Preferences'],
      output: 'Input Payload',
      targetTab: 'studio'
    },
    {
      id: 2,
      title: 'Content Agent',
      badge: 'LLM – Gemini',
      category: 'AI / LLM Component',
      catColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
      icon: Sparkles,
      color: 'from-emerald-500/20 to-teal-600/20 text-emerald-400 border-emerald-500/30',
      items: ['Generates post idea & script', 'Creates structured JSON', 'Suggests visual prompts', 'Adds hashtags & CTA'],
      output: 'Structured Content',
      targetTab: 'studio'
    },
    {
      id: 3,
      title: 'Media Decision Engine',
      badge: 'Rule-based + LLM',
      category: 'System / Business Logic',
      catColor: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
      icon: Layers,
      color: 'from-purple-500/20 to-pink-600/20 text-purple-400 border-purple-500/30',
      items: ['Checks for existing media', 'Validates file (if available)', 'Decides: Use / Generate', 'Selects Image or Video path'],
      output: 'Media Plan',
      targetTab: 'library'
    },
    {
      id: 4,
      title: 'Video / Image Production',
      badge: 'Gemini + TTS + FFmpeg',
      category: 'External Service / API',
      catColor: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
      icon: Video,
      color: 'from-cyan-500/20 to-blue-600/20 text-cyan-400 border-cyan-500/30',
      items: ['Video: Veo clips + TTS + SRT + FFmpeg', 'Image: Gemini image gen + optimize'],
      output: 'Final Media (MP4 / Image)',
      targetTab: 'library'
    },
    {
      id: 5,
      title: 'Compliance Agent',
      badge: 'LLM + Rules',
      category: 'AI / LLM Component',
      catColor: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
      icon: ShieldCheck,
      color: 'from-amber-500/20 to-orange-600/20 text-amber-400 border-amber-500/30',
      items: ['Checks content & media', 'Validates brand guidelines', 'Checks legal/regulatory rules', 'Auto-correct (up to 3 retries)'],
      output: 'Compliance Status',
      targetTab: 'review'
    },
    {
      id: 6,
      title: 'Autonomous Approval',
      badge: 'System',
      category: 'System / Business Logic',
      catColor: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
      icon: CheckCircle2,
      color: 'from-rose-500/20 to-pink-600/20 text-rose-400 border-rose-500/30',
      items: ['Checks compliance result', 'Validates media & metadata', 'Auto-approves if all pass', 'Blocks if failed'],
      output: 'Approval Status',
      targetTab: 'review'
    },
    {
      id: 7,
      title: 'LinkedIn Publisher',
      badge: 'LinkedIn API',
      category: 'External Service / API',
      catColor: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30',
      icon: LinkedinIcon,
      color: 'from-blue-600/20 to-sky-600/20 text-sky-400 border-sky-500/30',
      items: ['Upload media (if video)', 'Create post with content', 'Attach media asset', 'Get post ID / URL & retry backoff'],
      output: 'Publish Status + Post URL',
      targetTab: 'studio'
    },
    {
      id: 8,
      title: 'Evidence Collection',
      badge: 'Backend Service',
      category: 'Data / Storage',
      catColor: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30',
      icon: FileText,
      color: 'from-indigo-500/20 to-violet-600/20 text-indigo-400 border-indigo-500/30',
      items: ['Capture final content & media', 'Store compliance & approval logs', 'Save LinkedIn API response', 'Generate HD PDF evidence package'],
      output: 'Evidence Data & PDF',
      targetTab: 'review'
    },
    {
      id: 9,
      title: 'Feedback Memory',
      badge: 'Database',
      category: 'Data / Storage',
      catColor: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
      icon: Database,
      color: 'from-blue-500/20 to-teal-600/20 text-teal-400 border-teal-500/30',
      items: ['Store content, media, logs', 'Track performance metrics', 'Learn from engagement', 'Feeds back to Content Agent'],
      output: 'Updated Knowledge',
      targetTab: 'learning'
    }
  ];

  return (
    <div className="bg-[#0b1220]/95 border border-slate-800 rounded-2xl p-5 space-y-5 shadow-2xl backdrop-blur relative overflow-hidden">
      
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h3 className="text-sm font-bold tracking-wide text-white uppercase font-mono">
              NEXORA — Current Implementation Architecture
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            AI-Powered Social Media Marketing Platform for JA ASSURE
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono">
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> AI / LLM
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" /> External API
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400" /> System Logic
          </span>
          <span className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" /> Data / Storage
          </span>
        </div>
      </div>

      {/* Row 1: Pipeline Flow (Steps 1 to 5) */}
      <div className="space-y-1.5">
        <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-400 block">
          Phase 1: Generation & Verification
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {workflowSteps.slice(0, 5).map((step, idx) => {
            const Icon = step.icon;
            const isCurrentActive = activeStage === step.id;
            const isSelected = selectedStep === step.id;

            return (
              <div
                key={step.id}
                onClick={() => {
                  setSelectedStep(isSelected ? null : step.id);
                  if (onNavigate) onNavigate(step.targetTab);
                }}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between space-y-2 relative group ${
                  isCurrentActive
                    ? 'bg-gradient-to-b from-cyan-950/80 to-slate-900 border-cyan-400 shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400/50'
                    : isSelected
                    ? 'bg-slate-800/90 border-slate-600 shadow-md'
                    : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1.5">
                    <span className="text-[9px] font-mono font-bold text-slate-400">0{step.id}</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${step.catColor}`}>
                      {step.badge}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mb-1">
                    <div className="p-1 rounded-lg bg-slate-800/80 text-white shrink-0">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <h4 className="text-xs font-bold text-white leading-tight">{step.title}</h4>
                  </div>

                  <ul className="text-[10px] text-slate-400 space-y-0.5 mt-2 font-sans">
                    {step.items.map((it, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-slate-400 shrink-0">•</span>
                        <span className="truncate">{it}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
                  <span className="text-slate-400 font-mono">Output:</span>
                  <span className="font-semibold text-emerald-400 font-mono truncate max-w-[130px]">{step.output}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Row 2: Publishing, Evidence & Closed Feedback Loop (Steps 6 to 9 + Database) */}
      <div className="space-y-1.5 pt-1">
        <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-slate-400 block">
          Phase 2: Autonomous Publishing, Evidence & Feedback Loop
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {workflowSteps.slice(5, 9).map((step) => {
            const Icon = step.icon;
            const isCurrentActive = activeStage === step.id;
            const isSelected = selectedStep === step.id;

            return (
              <div
                key={step.id}
                onClick={() => {
                  setSelectedStep(isSelected ? null : step.id);
                  if (onNavigate) onNavigate(step.targetTab);
                }}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between space-y-2 relative group ${
                  isCurrentActive
                    ? 'bg-gradient-to-b from-cyan-950/80 to-slate-900 border-cyan-400 shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400/50'
                    : isSelected
                    ? 'bg-slate-800/90 border-slate-600 shadow-md'
                    : 'bg-slate-900/70 border-slate-800 hover:border-slate-700 hover:bg-slate-900/90'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-1 mb-1.5">
                    <span className="text-[9px] font-mono font-bold text-slate-400">0{step.id}</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded border ${step.catColor}`}>
                      {step.badge}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mb-1">
                    <div className="p-1 rounded-lg bg-slate-800/80 text-white shrink-0">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <h4 className="text-xs font-bold text-white leading-tight">{step.title}</h4>
                  </div>

                  <ul className="text-[10px] text-slate-400 space-y-0.5 mt-2 font-sans">
                    {step.items.map((it, i) => (
                      <li key={i} className="flex items-start gap-1">
                        <span className="text-slate-400 shrink-0">•</span>
                        <span className="truncate">{it}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
                  <span className="text-slate-400 font-mono">Output:</span>
                  <span className="font-semibold text-cyan-400 font-mono truncate max-w-[130px]">{step.output}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Closed Feedback Loop Banner */}
      <div className="p-3.5 rounded-xl bg-gradient-to-r from-blue-950/40 via-teal-950/30 to-slate-900 border border-teal-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center shrink-0 border border-teal-500/30">
            <RefreshCw className="w-4 h-4 animate-spin-slow" />
          </div>
          <div>
            <span className="font-bold text-white text-xs flex items-center gap-2">
              Closed Feedback Memory Loop
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded border border-emerald-500/20">
                Active Reinforcement
              </span>
            </span>
            <p className="text-[11px] text-slate-300 mt-0.5">
              Feedback Memory & Analytics flow back into the <strong>Content Agent (Gemini)</strong> to continuously improve future post ideas, hooks, and compliance accuracy.
            </p>
          </div>
        </div>

        <button
          onClick={() => onNavigate && onNavigate('learning')}
          className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-teal-600/30 hover:bg-teal-600/50 text-teal-200 border border-teal-500/40 transition-all flex items-center gap-1.5 shrink-0 cursor-pointer self-end sm:self-auto"
        >
          View Lessons Database
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

    </div>
  );
};
