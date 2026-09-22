import React, { useEffect, useState } from 'react';
import {
  Search,
  Globe,
  ExternalLink,
  Sparkles,
  Lightbulb,
  History,
  RefreshCw,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import type { Competitor, CompetitorDigestEntry, CompetitorSnapshot } from '../../types';
import { api } from '../../services/api';

interface CompetitorIntelViewProps {
  competitors: Competitor[];
  scrapeUrlInput: string;
  setScrapeUrlInput: (url: string) => void;
  scrapeBrand: 'jade' | 'doctorshield' | 'jaguartransit';
  setScrapeBrand: (brand: 'jade' | 'doctorshield' | 'jaguartransit') => void;
  scrapeResult: any;
  actionLoading: string | null;
  onScrape: () => void;
  getSourceTypeBadge: (source?: string, sourceType?: string) => React.ReactNode;
  getBrandBadge: (brand: string) => React.ReactNode;
}

export const CompetitorIntelView: React.FC<CompetitorIntelViewProps> = ({
  competitors,
  scrapeUrlInput,
  setScrapeUrlInput,
  scrapeBrand,
  setScrapeBrand,
  scrapeResult,
  actionLoading,
  onScrape,
  getSourceTypeBadge,
  getBrandBadge
}) => {
  const isScraping = actionLoading === 'scraping';

  const [digests, setDigests] = useState<CompetitorDigestEntry[]>([]);
  const [digestsLoading, setDigestsLoading] = useState(false);
  const [digestsError, setDigestsError] = useState<string | null>(null);
  const [expandedSnapshotsFor, setExpandedSnapshotsFor] = useState<number | null>(null);
  const [snapshotsByCompetitor, setSnapshotsByCompetitor] = useState<Record<number, CompetitorSnapshot[]>>({});

  const loadDigests = async () => {
    setDigestsLoading(true);
    setDigestsError(null);
    try {
      const result = await api.getCompetitorDigests();
      setDigests(result);
    } catch (err: any) {
      setDigestsError(err.message || 'Failed to load competitor change digest.');
    } finally {
      setDigestsLoading(false);
    }
  };

  useEffect(() => {
    loadDigests();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [competitors.length]);

  const toggleSnapshots = async (competitorId: number) => {
    if (expandedSnapshotsFor === competitorId) {
      setExpandedSnapshotsFor(null);
      return;
    }
    setExpandedSnapshotsFor(competitorId);
    if (!snapshotsByCompetitor[competitorId]) {
      try {
        const snaps = await api.getCompetitorSnapshots(competitorId);
        setSnapshotsByCompetitor((prev) => ({ ...prev, [competitorId]: snaps }));
      } catch {
        setSnapshotsByCompetitor((prev) => ({ ...prev, [competitorId]: [] }));
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Live Scraper & Competitor Extraction Command Panel */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
          <div>
            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
              <Search className="w-4 h-4 text-cyan-400" />
              Live Competitor Scraper & Intelligence Extractor
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Source-backed competitive intelligence engine enforcing strict timeouts and payload limits
            </p>
          </div>
          <span className="text-[10px] font-mono text-cyan-300 bg-cyan-500/10 border border-cyan-500/30 px-2.5 py-1 rounded-full w-fit">
            Deterministic Web Scraper
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 text-xs">
          <div className="md:col-span-3">
            <label className="text-slate-300 font-medium block">Counter-Brand Persona</label>
            <select
              value={scrapeBrand}
              onChange={(e) => setScrapeBrand(e.target.value as any)}
              className="w-full mt-1.5 bg-slate-900 border border-slate-700 rounded-xl p-2.5 text-slate-200 focus:ring-1 focus:ring-cyan-500"
            >
              <option value="jade">Jade (Luxury Jewellery)</option>
              <option value="doctorshield">DoctorShield (Med Indemnity)</option>
              <option value="jaguartransit">Jaguar Transit (Cargo)</option>
            </select>
          </div>

          <div className="md:col-span-6">
            <label className="text-slate-300 font-medium block">Competitor URL / Public Domain</label>
            <div className="relative mt-1.5">
              <Globe className="w-4 h-4 text-slate-500 absolute left-3 top-3 pointer-events-none" />
              <input
                type="text"
                value={scrapeUrlInput}
                onChange={(e) => setScrapeUrlInput(e.target.value)}
                placeholder="https://competitor.com/insurance-policy"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl py-2.5 pl-9 pr-3 text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500 font-mono"
              />
            </div>
          </div>

          <div className="md:col-span-3 flex items-end">
            <button
              onClick={onScrape}
              disabled={isScraping || !scrapeUrlInput}
              className="w-full py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-cyan-600/20 transition-all cursor-pointer disabled:opacity-50"
            >
              <Search className="w-3.5 h-3.5" />
              {isScraping ? 'Extracting Intelligence...' : 'Scrape & Analyze'}
            </button>
          </div>
        </div>

        {/* Recently Analyzed URL Result Banner */}
        {scrapeResult && (
          <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-800/40 text-xs space-y-2 mt-2">
            <div className="flex items-center justify-between">
              <span className="font-bold text-cyan-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" /> Extracted Intelligence: {scrapeResult.name}
              </span>
              <span className="font-mono text-[10px] text-cyan-400">{scrapeResult.website}</span>
            </div>
            <p className="text-slate-300 font-sans leading-relaxed">{scrapeResult.positioning}</p>
          </div>
        )}
      </div>

      {/* Competitor Change Digest -- real snapshot-vs-snapshot diffs, never fabricated */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center">
              <Lightbulb className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-100 flex items-center gap-2">
                Competitor Change Digest
              </h3>
              <p className="text-[11px] text-slate-400">
                Detected differences between this competitor's most recent two research snapshots -- factual, sourced, never invented
              </p>
            </div>
          </div>
          <button
            onClick={loadDigests}
            disabled={digestsLoading}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 cursor-pointer transition-colors"
            title="Refresh digest"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${digestsLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {digestsError ? (
          <div className="text-center py-6 text-xs text-rose-400">{digestsError}</div>
        ) : digests.length === 0 ? (
          <div className="text-center py-8 text-xs text-slate-500">
            No digest entries yet. Run research on a competitor at least twice to detect real changes over time.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {digests.map((d) => (
              <div key={d.competitor_id} className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2.5 flex flex-col justify-between">
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-xs text-slate-200">{d.competitor_name}</h4>
                    {d.has_change ? (
                      <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">Change Detected</span>
                    ) : (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-500 border border-slate-700">No Change</span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono capitalize">{d.category} • {d.source_type}</p>
                  {d.note && <p className="text-[11px] text-slate-500 italic">{d.note}</p>}
                  {d.changed_fields.length > 0 && (
                    <p className="text-[11px] text-slate-400 font-mono">Changed: {d.changed_fields.join(', ')}</p>
                  )}
                  {d.why_it_matters && (
                    <p className="text-[11px] text-slate-300 leading-relaxed font-sans">{d.why_it_matters}</p>
                  )}
                  {d.suggested_action && (
                    <p className="text-[11px] text-amber-200/90 leading-relaxed border-t border-slate-800/80 pt-1.5 mt-1.5">
                      <span className="font-bold text-amber-400">Suggested action: </span>{d.suggested_action}
                    </p>
                  )}
                </div>
                <div className="pt-2 border-t border-slate-800/80 text-[10px] font-mono text-slate-500">
                  Detected: {d.detected_at ? new Date(d.detected_at).toLocaleString() : '—'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Competitor Cards Grid */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Globe className="w-4 h-4 text-cyan-400" />
          Tracked Competitors & Observed Claims ({competitors.length})
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {competitors.map((c) => (
            <div key={c.id} className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4 hover:border-slate-700 transition-all">
              <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 pb-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-sm text-slate-100">{c.name}</h4>
                    {getSourceTypeBadge(c.source, c.source_type)}
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                    <span className="capitalize">{c.category}</span>
                    {c.url && (
                      <>
                        <span>•</span>
                        <a
                          href={c.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-cyan-400 hover:underline inline-flex items-center gap-1 truncate max-w-xs"
                        >
                          {c.url}
                          <ExternalLink className="w-2.5 h-2.5 shrink-0" />
                        </a>
                      </>
                    )}
                  </div>
                </div>

                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-cyan-950/40 text-cyan-400 border border-cyan-800/40">
                  {(c.relevance * 100).toFixed(0)}% Conf
                </span>
              </div>

              <div className="space-y-3 text-xs">
                {/* Title & Summary */}
                <div>
                  <h5 className="font-semibold text-slate-200 text-xs">{c.title}</h5>
                  <p className="text-slate-400 mt-1 leading-relaxed font-sans">{c.summary}</p>
                </div>

                {/* Observed Positioning & Claims */}
                {c.detected_change && (
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-slate-300 space-y-1">
                    <span className="text-[10px] font-mono text-cyan-400 uppercase font-semibold block">Observed Claims & Positioning</span>
                    <p className="text-[11px] text-slate-300 leading-relaxed">{c.detected_change}</p>
                  </div>
                )}

                {/* Strategic Whitespace / Recommendation */}
                {c.actionable_recommendation && (
                  <div className="p-3 rounded-xl bg-amber-950/20 border border-amber-900/30 text-amber-200 space-y-1">
                    <span className="font-bold font-mono text-[10px] uppercase text-amber-400 block">JA Assure Counter-Positioning Whitespace</span>
                    <p className="text-[11px] text-amber-200/90 leading-relaxed">{c.actionable_recommendation}</p>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span>Source: {c.source || 'Scraped Portal'}</span>
                <span>Collected: {c.collected_at ? new Date(c.collected_at).toLocaleDateString() : 'Active'}</span>
              </div>

              <button
                onClick={() => toggleSnapshots(c.id)}
                className="w-full flex items-center justify-center gap-1.5 text-[10px] font-mono text-slate-500 hover:text-slate-300 pt-1 cursor-pointer"
              >
                <History className="w-3 h-3" />
                Snapshot History
                {expandedSnapshotsFor === c.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>

              {expandedSnapshotsFor === c.id && (
                <div className="space-y-2 pt-1 border-t border-slate-800/60">
                  {(snapshotsByCompetitor[c.id] || []).length === 0 ? (
                    <p className="text-[11px] text-slate-500 text-center py-2">No snapshots recorded for this competitor yet.</p>
                  ) : (
                    snapshotsByCompetitor[c.id].map((s) => (
                      <div key={s.id} className="p-2.5 rounded-lg bg-slate-950/50 border border-slate-800/80 text-[11px] space-y-1">
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                          <span>{s.source_type}</span>
                          <span>{s.captured_at ? new Date(s.captured_at).toLocaleString() : '—'}</span>
                        </div>
                        <p className="text-slate-300 font-semibold">{s.title}</p>
                        <p className="text-slate-400 leading-relaxed">{s.summary}</p>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
