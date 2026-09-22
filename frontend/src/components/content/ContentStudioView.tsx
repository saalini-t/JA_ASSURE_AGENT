import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Send, 
  Copy, 
  ShieldCheck, 
  BrainCircuit, 
  Search, 
  Wand2,
  Volume2,
  Download,
  RefreshCw,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';
import type { GeneratedVariation, VideoScript, LessonLearned, Competitor, VoiceGenerationResponse } from '../../types';
import { api, API_ORIGIN, getMediaUrl } from '../../services/api';

interface ContentStudioViewProps {
  studioBrand: 'jade' | 'doctorshield' | 'jaguartransit';
  setStudioBrand: (brand: 'jade' | 'doctorshield' | 'jaguartransit') => void;
  studioPlatform: string;
  setStudioPlatform: (platform: string) => void;
  studioLanguage: string;
  setStudioLanguage: (language: string) => void;
  studioTopic: string;
  setStudioTopic: (topic: string) => void;
  generatedVariations: GeneratedVariation[];
  videoScript: VideoScript | null;
  actionLoading: string | null;
  onGenerateVariations: () => void;
  onLaunchFullSuite: () => void;
  onRunFullCampaign: () => void;
  showToast: (msg: string) => void;
  lessons: LessonLearned[];
  competitors: Competitor[];
}

export const ContentStudioView: React.FC<ContentStudioViewProps> = ({
  studioBrand,
  setStudioBrand,
  studioPlatform,
  setStudioPlatform,
  studioLanguage,
  setStudioLanguage,
  studioTopic,
  setStudioTopic,
  generatedVariations,
  videoScript,
  actionLoading,
  onGenerateVariations,
  onLaunchFullSuite,
  onRunFullCampaign,
  showToast,
  lessons,
  competitors
}) => {
  const [selectedSubTab, setSelectedSubTab] = useState<'content' | 'compliance' | 'research' | 'lessons'>('content');
  const [voiceLoading, setVoiceLoading] = useState(false);
  const [voiceResult, setVoiceResult] = useState<VoiceGenerationResponse | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);

  // Reset voice state whenever a fresh video script is produced
  useEffect(() => {
    setVoiceResult(null);
    setVoiceError(null);
  }, [videoScript]);

  const handleGenerateVoiceover = async () => {
    if (!videoScript) return;
    setVoiceLoading(true);
    setVoiceError(null);
    try {
      const res = await api.generateVoiceover(videoScript, studioLanguage);
      setVoiceResult(res);
      showToast('🔊 Real MP3 voiceover synthesized with gTTS and ready to play!');
    } catch (err: any) {
      console.error(err);
      const msg = err.message || 'Voiceover synthesis failed.';
      setVoiceError(msg);
      showToast(`✕ Voiceover generation failed: ${msg}`);
    } finally {
      setVoiceLoading(false);
    }
  };

  const isGenerating = actionLoading === 'generating';
  const isExecutingSuite = actionLoading === 'suite';
  const isRunningCampaign = actionLoading === 'campaign';
  const isVideoMode = studioPlatform === 'reel' || studioPlatform === 'video';

  // Count relevant active lessons for this brand
  const activeBrandLessons = lessons.filter(l => l.active);
  const brandCompetitors = competitors;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* LEFT COLUMN (4 Cols): Campaign Configuration */}
      <div className="lg:col-span-4 space-y-5">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Campaign Configuration
            </h3>
            <span className="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              Parameters
            </span>
          </div>

          <div className="space-y-3.5 text-xs">
            {/* Brand Persona Selector */}
            <div>
              <label className="text-slate-300 font-medium block">Brand Persona</label>
              <select
                value={studioBrand}
                onChange={(e) => setStudioBrand(e.target.value as any)}
                className="w-full mt-1.5 bg-slate-900 border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-200 focus:ring-1 focus:ring-amber-500 cursor-pointer font-medium"
              >
                <option value="jade">Jade (Luxury Jewellery & Private Wealth)</option>
                <option value="doctorshield">DoctorShield (Medical Professional Indemnity)</option>
                <option value="jaguartransit">Jaguar Transit (High-Risk Cargo & Transit)</option>
              </select>
            </div>

            {/* Target Platform */}
            <div>
              <label className="text-slate-300 font-medium block">Distribution Format / Channel</label>
              <select
                value={studioPlatform}
                onChange={(e) => setStudioPlatform(e.target.value)}
                className="w-full mt-1.5 bg-slate-900 border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-200 focus:ring-1 focus:ring-amber-500 cursor-pointer font-medium"
              >
                <option value="linkedin">LinkedIn Post (Executive / Risk Advisory)</option>
                <option value="instagram">Instagram Carousel / Caption (Visual Storytelling)</option>
                <option value="reel">Instagram / TikTok Reel (45s Production Cue Sheet)</option>
                <option value="video">Explainer Video Script (60s Multi-Scene Storyboard)</option>
                <option value="blog">InsurTech Editorial / Thought Leadership</option>
                <option value="email">VIP Underwriting Newsletter / Broker Note</option>
              </select>
            </div>

            {/* Language & Regional Localization */}
            <div>
              <label className="text-slate-300 font-medium block">Regional Localization</label>
              <select
                value={studioLanguage}
                onChange={(e) => setStudioLanguage(e.target.value)}
                className="w-full mt-1.5 bg-slate-900 border border-slate-700/80 rounded-xl p-2.5 text-xs text-slate-200 focus:ring-1 focus:ring-amber-500 cursor-pointer"
              >
                <option value="en">English (Singapore / International)</option>
                <option value="ms">Bahasa Melayu (Malaysia & Brunei)</option>
                <option value="id">Bahasa Indonesia (Jakarta / SEA)</option>
                <option value="th">Thai (ภาษาไทย - Bangkok)</option>
                <option value="zh">Chinese (Simplified / 简体中文)</option>
              </select>
            </div>

            {/* Campaign Topic & Problem Brief */}
            <div>
              <label className="text-slate-300 font-medium block">Campaign Brief & Problem Angle</label>
              <textarea
                rows={4}
                value={studioTopic}
                onChange={(e) => setStudioTopic(e.target.value)}
                className="w-full mt-1.5 bg-slate-900 border border-slate-700/80 rounded-xl p-3 text-xs text-slate-200 focus:ring-1 focus:ring-amber-500 leading-relaxed"
                placeholder="Describe the coverage problem, target demographic, or insurance vulnerability..."
              />
            </div>

            {/* Action Buttons */}
            <div className="pt-2 space-y-2">
              <button
                onClick={onGenerateVariations}
                disabled={isGenerating || isExecutingSuite}
                className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-amber-500/20 transition-all cursor-pointer disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5 text-slate-950" />
                {isGenerating ? 'Synthesizing with Groq...' : isVideoMode ? 'Generate AI Video Storyboard' : 'Generate A/B Variations'}
              </button>

              <button
                onClick={onLaunchFullSuite}
                disabled={isGenerating || isExecutingSuite || isRunningCampaign}
                className="w-full py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 font-semibold text-xs border border-slate-700/80 flex items-center justify-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5 text-cyan-400" />
                {isExecutingSuite ? 'Executing Full Brain Suite...' : 'Execute Full Pipeline Suite'}
              </button>

              <button
                onClick={onRunFullCampaign}
                disabled={isGenerating || isExecutingSuite || isRunningCampaign}
                title="One sequential call: writes the copy AND generates its real image/video together, instead of separate steps"
                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-50"
              >
                <Wand2 className="w-3.5 h-3.5" />
                {isRunningCampaign
                  ? (isVideoMode ? 'Running Campaign (Video)...' : 'Running Campaign (Image)...')
                  : `Run Full Campaign (Content + ${isVideoMode ? 'Video' : 'Image'}, One Click)`}
              </button>
            </div>
          </div>
        </div>

        {/* Brand Persona Guide Mini-Card */}
        <div className="glass-panel p-4 rounded-xl border border-slate-800 text-xs space-y-2">
          <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold block">Active Brand Persona Guardrails</span>
          <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="font-semibold text-slate-200">
              {studioBrand === 'jade' ? 'Jade: Luxury, Discretion & Preservation' :
               studioBrand === 'doctorshield' ? 'DoctorShield: Clinical Rigor & Defensibility' :
               'Jaguar Transit: Velocity, Chain-of-Custody & Resilience'}
            </span>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              {studioBrand === 'jade' 
                ? 'Emphasizes bespoke private vault protection, agreed-value valuation, and discreet worldwide collector coverage.'
                : studioBrand === 'doctorshield'
                ? 'Addresses surgical dispute defense, SMC inquiry coverage, and statutory indemnity limits without diagnostic claims.'
                : 'Focuses on secured armored transit, port-to-port diamond logistics, and high-value cargo casualty guarantees.'}
            </p>
          </div>
        </div>
      </div>

      {/* CENTER COLUMN (5 Cols): AI Generation Workspace */}
      <div className="lg:col-span-5 space-y-4">
        {/* Workspace Detail Sub-tabs */}
        <div className="flex items-center gap-1.5 border-b border-slate-800/80 pb-2.5 overflow-x-auto">
          {[
            { id: 'content', label: 'Generated Copy', icon: Sparkles },
            { id: 'compliance', label: 'Regulatory Audit', icon: ShieldCheck },
            { id: 'research', label: 'Market Context', icon: Search },
            { id: 'lessons', label: 'Injected Lessons', icon: BrainCircuit }
          ].map(tab => {
            const Icon = tab.icon;
            const isActive = selectedSubTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setSelectedSubTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all cursor-pointer whitespace-nowrap ${
                  isActive 
                    ? 'bg-slate-800 text-amber-300 border border-amber-500/40' 
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Sub-tab 1: CONTENT (A/B Variations or Video Storyboard) */}
        {selectedSubTab === 'content' && (
          <div className="space-y-4">
            {isGenerating && (
              <div className="glass-panel p-10 rounded-2xl border border-amber-500/30 text-center space-y-3 animate-pulse">
                <div className="w-10 h-10 rounded-xl bg-amber-500/20 text-amber-300 flex items-center justify-center mx-auto">
                  <Sparkles className="w-5 h-5 animate-spin text-amber-400" />
                </div>
                <h4 className="text-sm font-bold text-slate-100">Synthesizing Persona Copy with Groq LLaMA 3.3</h4>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Querying Supabase lessons learned, filtering competitor positioning, and running deterministic MAS/MOH compliance check...
                </p>
              </div>
            )}

            {/* Video / Reels Storyboard Cue Sheet */}
            {!isGenerating && videoScript && (
              <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
                <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 pb-3">
                  <div>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 uppercase font-semibold">
                      AI-Generated Storyboard
                    </span>
                    <h3 className="text-sm font-bold text-slate-100 mt-1">{videoScript.title || videoScript.concept}</h3>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Target Duration: <span className="text-slate-200 font-mono">{videoScript.target_duration_seconds}s</span> • 
                      Format: <span className="text-slate-200 font-mono capitalize">{videoScript.target_platform || studioPlatform}</span> • 
                      Tone: <span className="text-slate-200 capitalize">{videoScript.voiceover_tone}</span>
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(videoScript, null, 2));
                      showToast('Storyboard JSON copied to clipboard!');
                    }}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white bg-slate-900 border border-slate-800 cursor-pointer"
                    title="Copy Cue Sheet"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>

                {videoScript.hook && (
                  <div className="p-3 bg-cyan-950/20 border border-cyan-800/40 rounded-xl text-xs text-cyan-200 font-sans">
                    <span className="font-bold text-cyan-400 font-mono uppercase mr-2">Opening Hook:</span>
                    "{videoScript.hook}"
                  </div>
                )}

                {/* Phase 1/2: Real assembled MP4 preview (per-scene visuals + voiceover + captions) */}
                {videoScript.render_status === 'completed' && videoScript.video_url && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between flex-wrap gap-1.5">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 uppercase font-semibold">
                        Real MP4 Generated
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {videoScript.video_duration_seconds}s • {videoScript.scenes_generated} scenes •{' '}
                        {(videoScript.fallback_scene_count ?? 0) === 0 && (videoScript.ai_generated_scene_count ?? 0) > 0
                          ? 'AI-Generated Visuals'
                          : (videoScript.ai_generated_scene_count ?? 0) === 0 && (videoScript.fallback_scene_count ?? 0) > 0
                          ? 'Fallback Visuals (Demo Mode)'
                          : videoScript.scene_image_sources
                          ? 'Mixed AI/Fallback Visuals'
                          : videoScript.image_source === 'branded_fallback_demo'
                          ? 'Fallback Visuals (Demo Mode)'
                          : videoScript.image_source?.startsWith('mixed')
                          ? 'Mixed AI/Fallback Visuals'
                          : 'AI-Generated Visuals'}
                      </span>
                    </div>
                    <video
                      controls
                      className="w-full max-w-[280px] mx-auto rounded-xl border border-slate-800 bg-black"
                      src={`${API_ORIGIN}${videoScript.video_url}`}
                    />
                    <div className="flex items-center justify-center gap-2 flex-wrap">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        videoScript.has_audio
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}>
                        {videoScript.has_audio ? `✓ Voiceover (${videoScript.audio_source || 'audio'})` : '✕ No Voiceover'}
                      </span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                        videoScript.has_captions
                          ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                          : 'bg-slate-800 text-slate-400 border-slate-700'
                      }`}>
                        {videoScript.has_captions ? '✓ Captions Burned In' : '✕ No Captions'}
                      </span>
                    </div>

                    {/* Per-scene provider provenance -- exact honest phrasing, never
                        "AI generated" for a fallback scene. Preferred over the coarse
                        image_source summary above whenever the backend supplies it. */}
                    {videoScript.scene_image_sources && videoScript.scene_image_sources.length > 0 && (
                      <div className="space-y-1 pt-1">
                        {videoScript.scene_image_sources.map((s) => (
                          <div
                            key={s.scene_number}
                            className={`text-[10px] font-mono px-2 py-1 rounded-lg border flex items-center justify-between gap-2 ${
                              s.is_real_ai
                                ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30'
                                : 'bg-amber-950/20 text-amber-300 border-amber-800/30'
                            }`}
                          >
                            <span>Scene {s.scene_number}</span>
                            <span>
                              Visual source: {
                                s.source === 'gemini' ? 'Gemini — Cloud AI'
                                : s.source === 'huggingface' ? 'Hugging Face — Cloud AI'
                                : s.source === 'stable_diffusion_1_5' ? 'Stable Diffusion 1.5 — Local GPU'
                                : s.source === 'ai_generated_openai' ? 'OpenAI — Cloud AI'
                                : 'Branded fallback — AI provider unavailable'
                              }
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {((videoScript.fallback_scene_count ?? 0) > 0 || videoScript.image_source === 'branded_fallback_demo') && (
                      <p className="text-[10px] text-amber-300 bg-amber-950/20 border border-amber-800/30 rounded-lg p-2">
                        {videoScript.fallback_scene_count
                          ? `${videoScript.fallback_scene_count} scene(s) used the labeled branded fallback -- no configured AI image provider succeeded for them.`
                          : 'No OPENAI_API_KEY configured — scenes use labeled branded fallback cards, not AI-generated images.'}
                      </p>
                    )}
                  </div>
                )}
                {videoScript.render_status === 'failed' && (
                  <div className="text-[11px] text-rose-300 bg-rose-950/20 border border-rose-800/30 rounded-lg p-3">
                    Video rendering failed: {videoScript.render_error}
                  </div>
                )}

                {/* Standalone Voiceover Speech Studio Panel -- generates one combined
                    narration MP3 for the whole script via the Voice Agent (gTTS). This
                    is separate from the per-scene voiceover baked into the MP4 above
                    (Phase 2, when narrate=true) -- useful for previewing/downloading the
                    full narration track independently of a video render. */}
                <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/60 pb-2.5">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center">
                        <Volume2 className="w-4 h-4 text-cyan-400" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-slate-100 flex items-center gap-2">
                          Voice Agent & Audio Synthesis
                          {voiceResult ? (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> Voiceover Ready
                            </span>
                          ) : (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                              gTTS Engine
                            </span>
                          )}
                        </h4>
                        <p className="text-[11px] text-slate-400">
                          Synthesizes scene voiceovers into a single continuous MP3 audio track in {studioLanguage.toUpperCase()}
                        </p>
                      </div>
                    </div>

                    {!voiceResult && (
                      <button
                        onClick={handleGenerateVoiceover}
                        disabled={voiceLoading}
                        className="px-3.5 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-cyan-600/20 transition-all cursor-pointer w-fit"
                      >
                        {voiceLoading ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            Generating Voiceover...
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-3.5 h-3.5" />
                            Generate Voiceover
                          </>
                        )}
                      </button>
                    )}
                  </div>

                  {voiceLoading && (
                    <div className="py-4 text-center text-xs text-cyan-300 flex items-center justify-center gap-2 bg-slate-950/60 rounded-xl border border-cyan-500/20 animate-pulse">
                      <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                      Synthesizing scene voiceover copy with gTTS ({studioLanguage.toUpperCase()})...
                    </div>
                  )}

                  {voiceError && (
                    <div className="p-3 bg-rose-950/20 border border-rose-800/40 rounded-xl text-xs text-rose-300 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                        <span>{voiceError}</span>
                      </div>
                      <button
                        onClick={handleGenerateVoiceover}
                        className="text-[11px] underline hover:text-rose-100 font-semibold cursor-pointer"
                      >
                        Retry
                      </button>
                    </div>
                  )}

                  {voiceResult && (
                    <div className="space-y-3 pt-1">
                      {/* Audio Metadata Chips */}
                      <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          Lang: <strong className="text-cyan-300 uppercase">{voiceResult.language}</strong>
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          Provider: <strong className="text-slate-200 capitalize">{voiceResult.provider}</strong>
                        </span>
                        {voiceResult.duration_seconds && (
                          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            Duration: <strong className="text-emerald-300">{voiceResult.duration_seconds}s</strong>
                          </span>
                        )}
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                          Size: <strong className="text-slate-300">{(voiceResult.file_size_bytes / 1024).toFixed(1)} KB</strong>
                        </span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                          Scenes: {voiceResult.scene_count}
                        </span>
                      </div>

                      {/* Real HTML5 Audio Player */}
                      <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800">
                        <audio
                          key={voiceResult.audio_url}
                          controls
                          className="w-full h-10 accent-cyan-500 rounded-lg"
                        >
                          <source src={getMediaUrl(voiceResult.audio_url)} type="audio/mpeg" />
                          Your browser does not support the audio element.
                        </audio>
                      </div>

                      <div className="flex items-center justify-between gap-2 pt-1">
                        <span className="text-[10px] font-mono text-slate-500 truncate max-w-[280px]">
                          File: {voiceResult.audio_filename}
                        </span>
                        <div className="flex items-center gap-2">
                          <a
                            href={getMediaUrl(voiceResult.audio_url)}
                            download={voiceResult.audio_filename}
                            className="px-2.5 py-1 rounded-lg text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Download MP3
                          </a>
                          <button
                            onClick={handleGenerateVoiceover}
                            disabled={voiceLoading}
                            className="px-2.5 py-1 rounded-lg text-xs text-slate-400 hover:text-cyan-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
                            title="Regenerate speech audio"
                          >
                            <RefreshCw className="w-3.5 h-3.5" />
                            Re-synthesize
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Vertical Scene Timeline */}
                <div className="space-y-3 relative">
                  <div className="absolute left-4 top-4 bottom-4 w-0.5 bg-slate-800" />
                  {videoScript.scenes.map((scene) => (
                    <div key={scene.scene_number} className="relative pl-8 text-xs space-y-1 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
                      <div className="absolute left-2.5 top-4 w-3 h-3 rounded-full bg-cyan-500 border-2 border-slate-950 -translate-x-1/2" />
                      
                      <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                        <span className="font-bold text-slate-200">Scene {scene.scene_number}</span>
                        <span className="text-cyan-400 font-bold">{scene.duration_seconds}s</span>
                      </div>
                      <p><strong className="text-slate-400">Visual:</strong> {scene.visual_description}</p>
                      <p><strong className="text-slate-400">Voiceover:</strong> "{scene.voiceover}"</p>
                      <p className="text-cyan-300 font-mono"><strong className="text-slate-400">On-Screen Text:</strong> [{scene.onscreen_text}]</p>
                      {scene.transition && (
                        <p className="text-slate-400 font-mono text-[10px]"><strong className="text-slate-500">Transition:</strong> {scene.transition}</p>
                      )}
                      {scene.compliance_disclaimer && (
                        <p className="text-amber-300/90 text-[10px] bg-amber-950/20 px-2 py-0.5 rounded border border-amber-800/30">
                          <strong>Disclaimer Cue:</strong> {scene.compliance_disclaimer}
                        </p>
                      )}
                    </div>
                  ))}
                </div>

                <div className="text-[10px] text-slate-500 font-mono bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                  ℹ️ {videoScript.render_status === 'completed' || videoScript.render_status === 'failed'
                    ? 'Phase 1: scenes are rendered into a real MP4 using still images animated with FFmpeg pan/zoom. Voiceover, captions, and compliance are not implemented yet.'
                    : 'Production cue sheet format. Visual and audio directions are structured for video editors.'}
                </div>
              </div>
            )}

            {/* Standard A/B Variations Display */}
            {!isGenerating && !videoScript && generatedVariations.length > 0 && (
              <div className="space-y-4">
                {generatedVariations.map((v) => (
                  <div key={v.variation_label} className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
                      <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                        Variation {v.variation_label} • {v.variation_label === 'A' ? 'Professional / ROI Angle' : 'Emotional / Peace of Mind'}
                      </span>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(v.content_text);
                          showToast(`Variation ${v.variation_label} copied to clipboard!`);
                        }}
                        className="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 cursor-pointer"
                        title="Copy Copy"
                      >
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {v.headline && (
                      <h4 className="font-bold text-slate-100 text-xs">{v.headline}</h4>
                    )}

                    <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed bg-slate-900/80 p-3.5 rounded-xl border border-slate-800 font-sans">
                      {v.content_text}
                    </p>

                    {v.hashtags && v.hashtags.length > 0 && (
                      <div className="text-[11px] text-cyan-400 font-mono">
                        {v.hashtags.join(' ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Empty State */}
            {!isGenerating && !videoScript && generatedVariations.length === 0 && (
              <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center space-y-3">
                <Wand2 className="w-8 h-8 text-slate-600 mx-auto" />
                <h4 className="text-sm font-semibold text-slate-200">Creative Workspace Ready</h4>
                <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                  Configure your brand persona, format, and campaign topic on the left and click <strong>"Generate"</strong>. The agent will inject active lessons and evaluate compliance automatically.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Sub-tab 2: COMPLIANCE AUDIT EXPLANATION */}
        {selectedSubTab === 'compliance' && (
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3 text-xs">
            <h4 className="font-bold text-slate-200 uppercase font-mono text-[11px]">Automated 6-Rule MAS/MOH Audit Engine</h4>
            <div className="space-y-2 text-slate-300 leading-relaxed">
              <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-100">Superlatives & Guarantees:</strong>
                  <p className="text-[11px] text-slate-400">Strictly scans for words like "100%", "guaranteed payout", "zero risk", or "best in Singapore".</p>
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-100">Mandatory Statutory Disclaimers:</strong>
                  <p className="text-[11px] text-slate-400">Requires licensed intermediary advisory notes on all external marketing communications.</p>
                </div>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-slate-100">DoctorShield Medical Disclaimers:</strong>
                  <p className="text-[11px] text-slate-400">Prohibits providing clinical advice or promising malpractice indemnification outcome certainty.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sub-tab 3: RESEARCH CONTEXT */}
        {selectedSubTab === 'research' && (
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3 text-xs">
            <h4 className="font-bold text-slate-200 uppercase font-mono text-[11px]">Active Competitor Signals Considered</h4>
            <div className="space-y-2">
              {brandCompetitors.slice(0, 3).map((c) => (
                <div key={c.id} className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between font-mono text-[10px]">
                    <span className="text-cyan-400 font-semibold">{c.name}</span>
                    <span className="text-slate-500 capitalize">{c.category}</span>
                  </div>
                  <p className="text-[11px] text-slate-300 font-sans">{c.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sub-tab 4: INJECTED LESSONS */}
        {selectedSubTab === 'lessons' && (
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-3 text-xs">
            <h4 className="font-bold text-slate-200 uppercase font-mono text-[11px]">Closed-Loop Rules Influencing This Draft</h4>
            <div className="space-y-2">
              {activeBrandLessons.slice(0, 4).map((l) => (
                <div key={l.id} className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 space-y-1">
                  <div className="flex items-center justify-between font-mono text-[10px]">
                    <span className="text-purple-400 uppercase font-semibold">{l.category.replace(/_/g, ' ')}</span>
                    <span className="text-slate-500">Triggered {l.frequency}x</span>
                  </div>
                  <p className="text-[11px] text-slate-300 font-sans">{l.lesson}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN (3 Cols): AI Intelligence Panel */}
      <div className="lg:col-span-3 space-y-4">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
          <div className="border-b border-slate-800/80 pb-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              AI Intelligence Signals
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">Pre-generation telemetry</p>
          </div>

          <div className="space-y-3 text-xs">
            {/* Metric 1: Compliance Gauge */}
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-[11px]">Compliance Index</span>
                <span className="font-bold font-mono text-emerald-400 text-sm">85+ Target</span>
              </div>
              <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                <div className="w-[88%] h-full bg-emerald-500 rounded-full" />
              </div>
              <span className="text-[10px] text-slate-500 font-mono">Automated MAS & MOH Gate</span>
            </div>

            {/* Metric 2: Active Lessons */}
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-[11px]">Active Memory Rules</span>
                <span className="font-bold font-mono text-purple-300 text-sm">{activeBrandLessons.length}</span>
              </div>
              <span className="text-[10px] text-slate-500">Injected into system prompt</span>
            </div>

            {/* Metric 3: Research Signals */}
            <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-[11px]">Competitor Signals</span>
                <span className="font-bold font-mono text-cyan-300 text-sm">{brandCompetitors.length}</span>
              </div>
              <span className="text-[10px] text-slate-500">Market intelligence points</span>
            </div>

            {/* Metric 4: Human Review Required */}
            <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-800/40 space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-amber-300 text-[11px] font-semibold">Human Review Gate</span>
                <span className="font-bold font-mono text-amber-400 text-xs px-2 py-0.5 rounded bg-amber-500/20 border border-amber-500/30">
                  MANDATORY
                </span>
              </div>
              <span className="text-[10px] text-amber-200/70 block">
                Never automatically posted without explicit sign-off
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
