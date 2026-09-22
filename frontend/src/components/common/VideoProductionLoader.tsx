import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Video, 
  ImageIcon, 
  Volume2, 
  FileText, 
  Film, 
  CheckCircle2, 
  Loader2, 
  Clock, 
  ShieldCheck 
} from 'lucide-react';

interface VideoProductionLoaderProps {
  brand: string;
  topic: string;
  format?: string;
  language?: string;
}

export const VideoProductionLoader: React.FC<VideoProductionLoaderProps> = ({
  brand,
  topic,
  format = 'reel',
  language = 'en'
}) => {
  const [elapsed, setElapsed] = useState(0);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);

  const stages = [
    {
      id: 1,
      title: 'Script & Scene Engineering',
      desc: 'Google Gemini 3.5 Flash formulating scene breakdowns, hooks, and statutory disclosures',
      icon: Sparkles,
      color: 'text-amber-400',
      duration: 3
    },
    {
      id: 2,
      title: 'Photorealistic Visual Generation',
      desc: 'Compositing vertical HD commercial photography and bespoke scene assets (1080×1920)',
      icon: ImageIcon,
      color: 'text-cyan-400',
      duration: 3
    },
    {
      id: 3,
      title: 'Voiceover Narration Synthesis',
      desc: `gTTS Voice Agent synthesizing speech audio track in ${language.toUpperCase()}`,
      icon: Volume2,
      color: 'text-purple-400',
      duration: 3
    },
    {
      id: 4,
      title: 'Timestamped SRT Subtitle Sync',
      desc: 'Aligning precise millisecond captions with measured voiceover duration',
      icon: FileText,
      color: 'text-blue-400',
      duration: 2
    },
    {
      id: 5,
      title: 'FFmpeg Motion Assembly & Encoding',
      desc: 'Applying camera pan/zoom motion, burning in subtitles & exporting high-bitrate MP4',
      icon: Film,
      color: 'text-emerald-400',
      duration: 4
    }
  ];

  // Timer & Stage Progression
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed(prev => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (elapsed < 3) {
      setCurrentStageIndex(0);
    } else if (elapsed < 6) {
      setCurrentStageIndex(1);
    } else if (elapsed < 9) {
      setCurrentStageIndex(2);
    } else if (elapsed < 12) {
      setCurrentStageIndex(3);
    } else {
      setCurrentStageIndex(4);
    }
  }, [elapsed]);

  const progressPercent = Math.min(96, Math.max(10, Math.round((elapsed / 16) * 100)));

  return (
    <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-cyan-500/40 bg-gradient-to-b from-[#0a1122] to-[#080d1a] space-y-6 shadow-2xl relative overflow-hidden">
      {/* Top Ambient Glow */}
      <div className="absolute -top-24 left-1/2 -translate-x-1/2 w-96 h-32 bg-cyan-500/15 blur-3xl pointer-events-none" />

      {/* Header with Live Counter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4 relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center text-cyan-300 shadow-lg shadow-cyan-500/20 animate-pulse">
            <Video className="w-5 h-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                Production Engine Active
              </span>
              <span className="text-[10px] font-mono text-slate-400 capitalize">
                Brand: <strong className="text-slate-200">{brand}</strong>
              </span>
              <span className="text-[10px] font-mono text-cyan-400 uppercase">
                Format: <strong className="text-cyan-300">{format}</strong>
              </span>
              <span className="text-[10px] font-mono text-slate-400 uppercase">
                Lang: <strong className="text-slate-200">{language}</strong>
              </span>
            </div>
            <h3 className="text-sm sm:text-base font-bold text-slate-100 mt-1">
              Rendering AI Video Storyboard & Motion MP4
            </h3>
          </div>
        </div>

        {/* Elapsed Timer Pill */}
        <div className="flex items-center gap-2 self-start sm:self-auto bg-slate-900/90 border border-slate-800 px-3.5 py-1.5 rounded-xl font-mono text-xs">
          <Clock className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
          <span className="text-slate-400 text-[11px]">Elapsed:</span>
          <span className="text-cyan-300 font-bold font-mono">{elapsed}s</span>
        </div>
      </div>

      {/* Topic Context Pill */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80 text-xs text-slate-300 font-sans flex items-start gap-2 relative z-10">
        <Sparkles className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="truncate">
          <span className="text-slate-400 font-mono uppercase text-[10px] mr-1.5 font-bold">Campaign Angle:</span>
          <span className="text-slate-200 font-medium">{topic}</span>
        </div>
      </div>

      {/* Smooth Progress Bar */}
      <div className="space-y-1.5 relative z-10">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-cyan-300 font-semibold flex items-center gap-1.5">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
            {stages[currentStageIndex]?.title}...
          </span>
          <span className="text-slate-400 font-bold">{progressPercent}%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800 p-0.5">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 via-cyan-400 to-emerald-400 rounded-full transition-all duration-500 shadow-sm shadow-cyan-400/50"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Multi-Stage Step Trackers */}
      <div className="space-y-2 relative z-10">
        {stages.map((st, idx) => {
          const Icon = st.icon;
          const isDone = currentStageIndex > idx;
          const isCurrent = currentStageIndex === idx;

          return (
            <div
              key={st.id}
              className={`p-3 rounded-xl border text-xs flex items-center justify-between gap-3 transition-all ${
                isCurrent
                  ? 'bg-slate-900/90 border-cyan-500/50 ring-1 ring-cyan-500/30 shadow-md'
                  : isDone
                  ? 'bg-slate-900/40 border-slate-800/60 opacity-80'
                  : 'bg-slate-950/30 border-slate-900 opacity-40'
              }`}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border ${
                  isDone 
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40' 
                    : isCurrent 
                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse' 
                    : 'bg-slate-900 text-slate-500 border-slate-800'
                }`}>
                  {isDone ? <CheckCircle2 className="w-4 h-4" /> : <Icon className="w-3.5 h-3.5" />}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-200 truncate">{st.title}</span>
                    {isCurrent && (
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 animate-pulse">
                        In Progress
                      </span>
                    )}
                    {isDone && (
                      <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        Complete
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 truncate mt-0.5">{st.desc}</p>
                </div>
              </div>

              {isCurrent && (
                <Loader2 className="w-4 h-4 animate-spin text-cyan-400 shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      {/* Compliance Notice Footer */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] font-mono text-slate-400">
        <span className="flex items-center gap-1.5 text-emerald-400/90">
          <ShieldCheck className="w-3.5 h-3.5" />
          Statutory compliance checks applied automatically
        </span>
        <span className="text-slate-500">
          1080×1920 9:16 Vertical HD
        </span>
      </div>
    </div>
  );
};
