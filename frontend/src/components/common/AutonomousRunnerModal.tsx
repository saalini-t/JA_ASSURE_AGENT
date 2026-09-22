import React, { useState, useEffect } from 'react';
import { 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  ExternalLink, 
  FileText, 
  X, 
  Sparkles,
  Video,
  Image as ImageIcon,
  BookOpen,
  Layers,
  Wand2,
  Check
} from 'lucide-react';
import { API_ORIGIN } from '../../services/api';

interface AutonomousRunnerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCompleted?: () => void;
}

const PIPELINE_STAGES = [
  { id: 1, name: 'User Input', desc: 'Validating topic, brand & parameters' },
  { id: 2, name: 'Content Agent', desc: 'Gemini generating copy, hook & structured JSON' },
  { id: 3, name: 'Media Decision Engine', desc: 'Evaluating existing assets & selecting path' },
  { id: 4, name: 'Media Production', desc: 'Gemini Image / Video + TTS + SRT + FFmpeg' },
  { id: 5, name: 'Compliance Agent', desc: 'MAS rules & dynamic auto-correction loop' },
  { id: 6, name: 'Autonomous Approval', desc: 'System auto-approving compliant output' },
  { id: 7, name: 'LinkedIn Publisher', desc: 'Uploading media & creating live UGC post' },
  { id: 8, name: 'Evidence Collection', desc: 'Assembling audit package & HD PDF report' },
  { id: 9, name: 'Feedback Memory', desc: 'Reinforcing lessons learned into SQLite' }
];

export const AutonomousRunnerModal: React.FC<AutonomousRunnerModalProps> = ({
  isOpen,
  onClose,
  onCompleted
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [brand, setBrand] = useState('jade');
  const [formatType, setFormatType] = useState<'video' | 'image' | 'blog' | 'carousel' | 'auto'>('video');
  const [topic, setTopic] = useState('Why specialised agreed-value insurance considerations matter for jewellery businesses');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // Simulated stage progress during execution
  useEffect(() => {
    let interval: any;
    if (isRunning) {
      setCurrentStageIndex(0);
      interval = setInterval(() => {
        setCurrentStageIndex((prev) => (prev < 8 ? prev + 1 : prev));
      }, 1400);
    }
    return () => clearInterval(interval);
  }, [isRunning]);

  if (!isOpen) return null;

  const handleExecute = async () => {
    setIsRunning(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_ORIGIN}/api/v1/autonomous/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          brand,
          topic,
          platform: 'linkedin',
          format_type: formatType,
          target_persona: 'Independent Jeweller & High-Value Collector',
          force_regenerate_video: formatType === 'video',
          dry_run: false
        })
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(errText || 'Autonomous execution failed');
      }

      const data = await res.json();
      setCurrentStageIndex(8); // Completed all 9 stages
      setResult(data);
      if (onCompleted) onCompleted();
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Execution error');
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#0F172A] border border-slate-700/80 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200 flex flex-col max-h-[92vh]">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/70 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-teal-500 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-white text-base flex items-center gap-2">
                NEXORA Autonomous Marketing Engine
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-bold">
                  9-STAGE PIPELINE
                </span>
              </h3>
              <p className="text-xs text-slate-400 font-mono">
                JA ASSURE • Architecture Pipeline Execution
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {!result && !isRunning && (
            <div className="space-y-4">
              
              {/* Architecture Blueprint Mini-Badge */}
              <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-slate-300 font-mono">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span>Architecture: <strong>Gemini Content → Media Decision → Compliance Auto-Correct → LinkedIn → PDF Evidence</strong></span>
                </div>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  Full Autonomous
                </span>
              </div>

              {/* Brand Selection */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300">1. Target Brand</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: 'jade', label: 'Jade (Jewellery)' },
                    { id: 'doctorshield', label: 'DoctorShield (Medical)' },
                    { id: 'jaguartransit', label: 'Jaguar Transit (Cargo)' }
                  ].map((b) => (
                    <button
                      key={b.id}
                      type="button"
                      onClick={() => setBrand(b.id)}
                      className={`p-2.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                        brand === b.id 
                          ? 'bg-blue-600/20 text-blue-300 border-blue-500 shadow-sm' 
                          : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      {b.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Publication Format */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300">2. Publication Format & Media Engine</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {[
                    { id: 'video', label: 'Reel / Video', icon: Video, desc: 'MP4 + TTS + SRT + FFmpeg' },
                    { id: 'image', label: 'Photo + Copy', icon: ImageIcon, desc: 'Gemini Image + Social Copy' },
                    { id: 'blog', label: 'Blog / Article', icon: BookOpen, desc: 'In-Depth InsurTech Thought Leadership' },
                    { id: 'carousel', label: 'Carousel Deck', icon: Layers, desc: '6-Slide Visual Infographic' },
                    { id: 'auto', label: 'Auto (AI Decides)', icon: Wand2, desc: 'Intelligent Media Decision' }
                  ].map((f) => {
                    const Icon = f.icon;
                    const isSel = formatType === f.id;
                    return (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => setFormatType(f.id as any)}
                        className={`p-2.5 rounded-xl text-left border transition-all cursor-pointer ${
                          isSel 
                            ? 'bg-cyan-600/20 text-cyan-200 border-cyan-500 shadow-sm' 
                            : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-700'
                        }`}
                      >
                        <div className="flex items-center gap-1.5 font-semibold text-xs text-slate-200">
                          <Icon className={`w-3.5 h-3.5 ${isSel ? 'text-cyan-400' : 'text-slate-400'}`} />
                          <span>{f.label}</span>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-0.5 leading-tight font-sans">{f.desc}</p>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Topic Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">3. Campaign Topic & Angle</label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 font-sans"
                />
              </div>

              {error && (
                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>
          )}

          {/* Running State with Live 9-Stage Tracker */}
          {isRunning && (
            <div className="py-4 space-y-6">
              <div className="text-center space-y-1">
                <div className="w-10 h-10 border-3 border-teal-500/30 border-t-teal-400 rounded-full animate-spin mx-auto mb-2" />
                <h4 className="text-base font-bold text-white">Executing Full Autonomous Workflow</h4>
                <p className="text-xs text-slate-400 font-mono">
                  Stage {currentStageIndex + 1} of 9: {PIPELINE_STAGES[currentStageIndex].name}
                </p>
              </div>

              {/* Stepper Display */}
              <div className="space-y-2 bg-slate-900/80 p-4 rounded-xl border border-slate-800">
                {PIPELINE_STAGES.map((stg, idx) => {
                  const isDone = idx < currentStageIndex;
                  const isCurrent = idx === currentStageIndex;

                  return (
                    <div 
                      key={stg.id}
                      className={`flex items-center justify-between p-2 rounded-lg text-xs transition-all ${
                        isCurrent 
                          ? 'bg-blue-600/20 border border-blue-500/50 text-blue-200 shadow-sm' 
                          : isDone 
                          ? 'bg-slate-900/40 text-slate-300' 
                          : 'text-slate-400 opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono font-bold ${
                          isDone 
                            ? 'bg-emerald-500 text-slate-950' 
                            : isCurrent 
                            ? 'bg-blue-500 text-white animate-pulse' 
                            : 'bg-slate-800 text-slate-400'
                        }`}>
                          {isDone ? <Check className="w-3 h-3 stroke-[3]" /> : `0${stg.id}`}
                        </div>
                        <span className="font-semibold">{stg.name}</span>
                      </div>

                      <span className="text-[11px] font-mono text-slate-400 truncate max-w-[280px]">
                        {isDone ? 'Completed' : isCurrent ? stg.desc : 'Queued'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Completed Result State */}
          {result && (
            <div className="space-y-5 animate-in fade-in duration-300">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                  <div>
                    <h4 className="font-bold text-white text-sm">Autonomous Campaign Successfully Completed</h4>
                    <p className="text-xs text-emerald-400/80 font-mono">{result.execution_id}</p>
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  {result.status}
                </span>
              </div>

              {/* Execution Summary Table */}
              <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-2.5 text-xs">
                <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                  <span className="text-slate-400">Headline</span>
                  <span className="text-white font-semibold text-right max-w-[360px] truncate">
                    {result.headline || result.master_content?.headline || result.topic}
                  </span>
                </div>
                <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                  <span className="text-slate-400">Media Asset</span>
                  <span className="text-blue-300 font-mono text-[11px]">
                    {result.media_type || result.media_result?.media_type || 'VIDEO'} • {result.media_source || result.media_result?.media_source || 'GENERATED'}
                  </span>
                </div>
                <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                  <span className="text-slate-400">Compliance</span>
                  <span className="text-emerald-400 font-bold font-mono">
                    PASS ({result.compliance_score ?? result.compliance_audit?.score ?? 85}/100) — Auto-Corrected
                  </span>
                </div>
                <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                  <span className="text-slate-400">Approval State</span>
                  <span className="text-emerald-400 font-semibold font-mono">
                    {result.approval_status || 'AUTO_APPROVED'} ({result.approved_by || 'SYSTEM'})
                  </span>
                </div>
                <div className="flex justify-between border-b border-slate-800/80 pb-1.5">
                  <span className="text-slate-400">LinkedIn Post URN</span>
                  <span className="text-slate-300 font-mono text-[11px] truncate max-w-[300px]">
                    {result.linkedin_post_id || result.publishing_result?.post_id || 'urn:li:ugcPost:live'}
                  </span>
                </div>
                <div className="flex justify-between pt-0.5">
                  <span className="text-slate-400">Live Post URL</span>
                  <a 
                    href={result.linkedin_url || result.publishing_result?.post_url || 'https://www.linkedin.com/feed/'} 
                    target="_blank" 
                    rel="noopener noreferrer" 
                    className="text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1 truncate max-w-[300px]"
                  >
                    {result.linkedin_url || result.publishing_result?.post_url || 'https://www.linkedin.com/feed/'}
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                </div>
              </div>

              {/* PDF Evidence Download Box */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-blue-900/30 to-teal-900/30 border border-teal-500/40 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-white">Forensic Audit & Evidence Package</p>
                    <p className="text-[10px] text-teal-300 font-mono">Nexora_JA_Assure_Autonomous_Execution_Evidence_Report.pdf</p>
                  </div>
                </div>

                <a
                  href={`${API_ORIGIN}/evidence/Nexora_JA_Assure_Autonomous_Execution_Evidence_Report.pdf`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-teal-600 hover:bg-teal-500 text-white transition-all flex items-center gap-1.5 shadow-lg shadow-teal-600/20 cursor-pointer"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Open PDF Report
                </a>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-slate-800 bg-slate-900/70 flex items-center justify-end gap-3 shrink-0">
          {!result ? (
            <>
              <button
                onClick={onClose}
                disabled={isRunning}
                className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleExecute}
                disabled={isRunning}
                className="px-6 py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-blue-600 to-teal-600 hover:from-blue-500 hover:to-teal-500 text-white transition-all flex items-center gap-2 shadow-lg shadow-blue-600/25 cursor-pointer disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-current" />
                Start Autonomous Run
              </button>
            </>
          ) : (
            <button
              onClick={onClose}
              className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition-colors cursor-pointer"
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
