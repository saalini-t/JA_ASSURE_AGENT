import { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Sparkles, 
  BrainCircuit, 
  Calendar, 
  Send,
  AlertCircle
} from 'lucide-react';
import { api } from './services/api';
import type { 
  DashboardSummary, 
  ContentQueueItem, 
  HealthCheckResponse, 
  Competitor, 
  Lead, 
  LessonLearned, 
  Feedback, 
  GeneratedVariation, 
  VideoScript, 
  PublishingRecord 
} from './types';

import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';
import { DashboardView } from './components/dashboard/DashboardView';
import { ContentStudioView } from './components/content/ContentStudioView';
import { ReviewCenterView } from './components/review/ReviewCenterView';
import { CompetitorIntelView } from './components/competitors/CompetitorIntelView';
import { LeadsView } from './components/leads/LeadsView';
import { PublishingView } from './components/publishing/PublishingView';
import { LearningView } from './components/learning/LearningView';
import { AnalyticsView } from './components/analytics/AnalyticsView';
import { Modals } from './components/common/Modals';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'studio' | 'review' | 'competitors' | 'leads' | 'publishing' | 'learning' | 'analytics'>('dashboard');
  const [selectedBrand, setSelectedBrand] = useState<string>('all');
  
  // Data states
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [queue, setQueue] = useState<ContentQueueItem[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [lessons, setLessons] = useState<LessonLearned[]>([]);
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [publishingRecords, setPublishingRecords] = useState<PublishingRecord[]>([]);
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Studio Form states
  const [studioBrand, setStudioBrand] = useState<'jade' | 'doctorshield' | 'jaguartransit'>('jade');
  const [studioPlatform, setStudioPlatform] = useState<string>('linkedin');
  const [studioLanguage, setStudioLanguage] = useState<string>('en');
  const [studioTopic, setStudioTopic] = useState<string>('Why Home Insurance Sub-Limits Fail Luxury Diamond Collections');
  const [generatedVariations, setGeneratedVariations] = useState<GeneratedVariation[]>([]);
  const [videoScript, setVideoScript] = useState<VideoScript | null>(null);

  // Review & Modals
  const [reviewFilter, setReviewFilter] = useState<'pending' | 'approved' | 'rejected' | 'all'>('pending');
  const [rejectModalItem, setRejectModalItem] = useState<ContentQueueItem | null>(null);
  const [rejectReasonTag, setRejectReasonTag] = useState<string>('false_guarantee');
  const [rejectNotes, setRejectNotes] = useState<string>('');
  
  const [editModalItem, setEditModalItem] = useState<ContentQueueItem | null>(null);
  const [editContentText, setEditContentText] = useState<string>('');

  // Publishing Preview Modal states
  const [publishingModalItem, setPublishingModalItem] = useState<ContentQueueItem | null>(null);
  const [scheduledPlatform, setScheduledPlatform] = useState<string>('linkedin');
  const [scheduledTime, setScheduledTime] = useState<string>('');

  // Scraper & Competitor Form
  const [scrapeUrlInput, setScrapeUrlInput] = useState<string>('https://briteprotect.example.com');
  const [scrapeBrand, setScrapeBrand] = useState<'jade' | 'doctorshield' | 'jaguartransit'>('jade');
  const [scrapeResult, setScrapeResult] = useState<any>(null);

  // Lead Discovery Filters & Enrichment
  const [leadCountry, setLeadCountry] = useState<string>('Singapore');
  const [leadBrand, setLeadBrand] = useState<string>('jade');
  const [leadIndustry, setLeadIndustry] = useState<string>('');
  const [enrichModalLead, setEnrichModalLead] = useState<Lead | null>(null);
  const [enrichUrlInput, setEnrichUrlInput] = useState<string>('');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, s, q, c, l, les, fb, pubs] = await Promise.all([
        api.getHealth(),
        api.getDashboardSummary(),
        api.getQueue({ brand: selectedBrand !== 'all' ? selectedBrand : undefined }),
        api.getCompetitors(),
        api.getLeads(),
        api.getLessons(),
        api.getFeedback(),
        api.getPublishingRecords()
      ]);
      setHealth(h);
      setSummary(s);
      setQueue(q);
      setCompetitors(c);
      setLeads(l);
      setLessons(les);
      setFeedbacks(fb);
      setPublishingRecords(pubs);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'AI Marketing API unavailable at http://localhost:8000.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, [selectedBrand]);

  // Review Actions
  const handleApprove = async (id: number) => {
    setActionLoading(`approve-${id}`);
    try {
      await api.approveContent(id, 'Human reviewer sign-off confirmed.');
      showToast('✓ Content approved and ready for publishing dispatch preview!');
      fetchAllData();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenReject = (item: ContentQueueItem) => {
    setRejectModalItem(item);
    setRejectReasonTag(item.reason_tag || 'false_guarantee');
    setRejectNotes('');
  };

  const handleConfirmReject = async () => {
    if (!rejectModalItem) return;
    setActionLoading(`reject-${rejectModalItem.id}`);
    try {
      await api.rejectContent(rejectModalItem.id, rejectReasonTag, rejectNotes || 'Rejected by reviewer');
      showToast('✕ Content rejected. Closed-loop lesson synthesized & injected for future prompts!');
      setRejectModalItem(null);
      fetchAllData();
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleOpenEdit = (item: ContentQueueItem) => {
    setEditModalItem(item);
    setEditContentText(item.content_raw);
  };

  const handleConfirmEdit = async () => {
    if (!editModalItem) return;
    setActionLoading(`edit-${editModalItem.id}`);
    try {
      await api.editContent(editModalItem.id, editContentText, 'human_edit', 'Verified and corrected during human review');
      showToast('✓ Content updated and resubmitted for human review (compliance re-checked)!');
      setEditModalItem(null);
      fetchAllData();
    } catch (err: any) {
      alert(`Edit error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRewrite = async (id: number) => {
    setActionLoading(`rewrite-${id}`);
    try {
      await api.rewriteContent(id);
      showToast('✨ AI Compliance Rewrite applied. Item re-evaluated and awaiting human sign-off!');
      fetchAllData();
    } catch (err: any) {
      alert(`Rewrite error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenerate = async (id: number) => {
    setActionLoading(`regen-${id}`);
    try {
      await api.regenerateContent(id);
      showToast('🔄 Content regenerated applying active lessons learned!');
      fetchAllData();
    } catch (err: any) {
      alert(`Regeneration error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Publishing Preview Handlers (Human-controlled simulated dispatch)
  const handleOpenScheduleModal = (item: ContentQueueItem) => {
    if (item.status !== 'approved' && item.status !== 'scheduled') {
      alert('Only human-approved content can reach simulated publishing dispatch preview.');
      return;
    }
    if (item.compliance_score < 80) {
      alert(`Cannot schedule non-compliant content (Score: ${item.compliance_score}/100).`);
      return;
    }
    setPublishingModalItem(item);
    setScheduledPlatform(item.platform || 'linkedin');
    
    // Default scheduled time: tomorrow at 09:00 AM local time
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(9, 0, 0, 0);
    const localIso = new Date(tomorrow.getTime() - tomorrow.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
    setScheduledTime(localIso);
  };

  const handleConfirmSchedule = async () => {
    if (!publishingModalItem) return;
    setActionLoading(`schedule-${publishingModalItem.id}`);
    try {
      await api.schedulePublishing({
        content_id: publishingModalItem.id,
        platform: scheduledPlatform,
        scheduled_at: scheduledTime ? new Date(scheduledTime).toISOString() : undefined
      });
      showToast(`✓ Simulated dispatch scheduled for ${scheduledPlatform.toUpperCase()}! Stored in Supabase.`);
      setPublishingModalItem(null);
      fetchAllData();
    } catch (err: any) {
      alert(`Scheduling error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleCancelPublishing = async (recordId: number) => {
    setActionLoading(`cancel-pub-${recordId}`);
    try {
      await api.cancelPublishing(recordId);
      showToast('Scheduled dispatch cancelled. Content item returned to approved pool.');
      fetchAllData();
    } catch (err: any) {
      alert(`Cancel error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Studio Generation
  const handleGenerateVariations = async () => {
    setActionLoading('generating');
    setGeneratedVariations([]);
    setVideoScript(null);
    try {
      if (studioPlatform === 'reel' || studioPlatform === 'video') {
        const script = await api.generateVideoScript({
          brand: studioBrand,
          topic: studioTopic,
          platform: studioPlatform,
          language: studioLanguage,
          target_duration: 45
        });
        setVideoScript(script);
        showToast('🎬 Structured 45s Video/Reels Storyboard generated!');
      } else {
        const vars = await api.generateVariations({
          brand: studioBrand,
          platform: studioPlatform,
          topic: studioTopic,
          language: studioLanguage
        });
        setGeneratedVariations(vars);
        showToast('✓ A/B marketing copy variations generated!');
      }
    } catch (err: any) {
      alert(`Generation failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleLaunchFullSuite = async () => {
    setActionLoading('suite');
    try {
      const created = await api.generateSuite({
        brand: studioBrand,
        topic: studioTopic,
        platforms: ['linkedin', 'instagram'],
        content_types: ['post'],
        languages: [studioLanguage]
      });
      showToast(`🚀 Full Pipeline Suite executed! ${created.length} drafts staged for Human Review.`);
      fetchAllData();
      setActiveTab('review');
    } catch (err: any) {
      alert(`Suite error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Competitor Analysis & Scraper
  const handleScrape = async () => {
    if (!scrapeUrlInput) return;
    setActionLoading('scraping');
    try {
      const comp = await api.analyzeCompetitorUrl(scrapeUrlInput, scrapeBrand);
      setScrapeResult(comp);
      showToast(`✓ Analyzed competitor & extracted strategic intelligence: ${comp.name}`);
      fetchAllData();
    } catch (err: any) {
      alert(`Scraping / Analysis error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Lead Discovery & Outreach
  const handleDiscoverLeadsWithFilters = async () => {
    setActionLoading('discovering');
    try {
      const prospects = await api.discoverLeads({
        brand: leadBrand !== 'all' ? leadBrand : undefined,
        country: leadCountry !== 'all' ? leadCountry : undefined,
        industry: leadIndustry || undefined
      });
      showToast(`✓ Discovered & scored ${prospects.length} B2B prospects!`);
      fetchAllData();
    } catch (err: any) {
      alert(`Discovery failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEnrichLead = async () => {
    if (!enrichModalLead) return;
    setActionLoading(`enrich-${enrichModalLead.id}`);
    try {
      const enriched = await api.enrichLead(enrichModalLead.id, enrichUrlInput || undefined);
      showToast(`✓ Enriched risk profile & outreach for ${enriched.company}!`);
      setEnrichModalLead(null);
      setEnrichUrlInput('');
      fetchAllData();
    } catch (err: any) {
      alert(`Enrichment error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  // Real LinkedIn Publishing (Project 2 "The Hands")
  const handlePublishToLinkedIn = async (contentId: number) => {
    setActionLoading(`linkedin-${contentId}`);
    try {
      const record = await api.publishToLinkedIn(contentId);
      showToast(record.status === 'published'
        ? `✓ Published to LinkedIn (post ${record.external_post_id || 'n/a'})!`
        : `Publish attempt recorded with status: ${record.status}.`);
      fetchAllData();
    } catch (err: any) {
      alert(`LinkedIn publish failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRefreshEngagement = async (recordId: number) => {
    setActionLoading(`refresh-${recordId}`);
    try {
      await api.refreshEngagementAnalytics(recordId);
      showToast('✓ Engagement analytics refresh attempted (see record for real result or honest "unavailable").');
      fetchAllData();
    } catch (err: any) {
      alert(`Analytics refresh failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRunWorkerOnce = async () => {
    setActionLoading('worker-run');
    try {
      const result = await api.runWorkerOnce();
      showToast(`✓ Worker pass complete: ${result.processed} item(s) processed.`);
      fetchAllData();
    } catch (err: any) {
      alert(`Worker run failed: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleLesson = async (lessonId: number) => {
    try {
      await api.toggleLesson(lessonId);
      fetchAllData();
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  // Badge Formatting Helpers
  const getSourceTypeBadge = (source?: string, sourceType?: string) => {
    const s = (sourceType || source || '').toUpperCase();
    if (s.includes('VERIFIED')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-emerald-400" /> VERIFIED SOURCE
        </span>
      );
    }
    if (s.includes('ANALYSIS')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-500/15 text-cyan-300 border border-blue-500/30 flex items-center gap-1">
          <BrainCircuit className="w-3 h-3 text-cyan-400" /> AI ANALYSIS
        </span>
      );
    }
    if (s.includes('PROSPECT') || s.includes('AI_GENERATED')) {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/15 text-amber-300 border border-amber-500/30 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-amber-400" /> AI-GENERATED PROSPECT
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-400 border border-slate-700">
        DEMO DATA
      </span>
    );
  };

  const getBrandBadge = (brand: string) => {
    switch (brand) {
      case 'jade':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">Jade (Jewellery)</span>;
      case 'doctorshield':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-300 border border-blue-500/30">DoctorShield (Med Indemnity)</span>;
      case 'jaguartransit':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">Jaguar Transit (Cargo)</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-700">{brand}</span>;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return <span className="inline-flex items-center gap-1 text-xs text-emerald-400 font-medium"><CheckCircle2 className="w-3.5 h-3.5" /> Approved</span>;
      case 'scheduled':
        return <span className="inline-flex items-center gap-1 text-xs text-cyan-300 font-semibold px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30"><Calendar className="w-3 h-3 text-cyan-400" /> Scheduled (Simulated)</span>;
      case 'published':
        return <span className="inline-flex items-center gap-1 text-xs text-blue-300 font-semibold px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/30"><Send className="w-3 h-3 text-blue-400" /> Published to LinkedIn</span>;
      case 'human_review':
        return <span className="inline-flex items-center gap-1 text-xs text-amber-400 font-medium"><Clock className="w-3.5 h-3.5" /> Awaiting Review</span>;
      case 'rejected':
        return <span className="inline-flex items-center gap-1 text-xs text-rose-400 font-medium"><XCircle className="w-3.5 h-3.5" /> Rejected</span>;
      default:
        return <span className="inline-flex items-center gap-1 text-xs text-slate-400 font-medium"><Clock className="w-3.5 h-3.5" /> {status}</span>;
    }
  };

  const pendingReviewCount = queue.filter(q => q.status === 'human_review' || q.status === 'pending').length;

  return (
    <div className="min-h-screen bg-[#080c16] text-slate-100 flex font-sans">
      {/* Toast Alert Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#0f172a] text-amber-300 px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 border border-amber-500/40 animate-bounce">
          <Sparkles className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="text-xs font-semibold">{toastMessage}</span>
        </div>
      )}

      {/* LEFT SIDEBAR */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingReviewCount={pendingReviewCount}
        health={health}
      />

      {/* MAIN COMMAND AREA */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        {/* Top Header Command Bar */}
        <Header
          activeTab={activeTab}
          selectedBrand={selectedBrand}
          setSelectedBrand={setSelectedBrand}
          health={health}
          loading={loading}
          onRefresh={fetchAllData}
        />

        {/* Workspaces Container */}
        <main className="p-6 md:p-8 flex-1 max-w-7xl w-full mx-auto space-y-6">
          {error && (
            <div className="p-4 rounded-2xl bg-rose-950/40 border border-rose-800/50 flex items-start gap-3 text-rose-200">
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div className="text-xs">
                <p className="font-bold text-rose-300">AI Marketing API Unavailable</p>
                <p className="text-rose-300/80 mt-0.5">{error}</p>
                <button
                  onClick={fetchAllData}
                  className="mt-2 px-3 py-1 rounded bg-rose-900/60 hover:bg-rose-900 text-rose-200 text-xs font-mono font-semibold cursor-pointer"
                >
                  Retry Connection
                </button>
              </div>
            </div>
          )}

          {/* 1. DASHBOARD VIEW */}
          {activeTab === 'dashboard' && (
            <DashboardView
              summary={summary}
              queue={queue}
              lessons={lessons}
              setActiveTab={setActiveTab}
              getBrandBadge={getBrandBadge}
              getStatusBadge={getStatusBadge}
            />
          )}

          {/* 2. CONTENT STUDIO VIEW */}
          {activeTab === 'studio' && (
            <ContentStudioView
              studioBrand={studioBrand}
              setStudioBrand={setStudioBrand}
              studioPlatform={studioPlatform}
              setStudioPlatform={setStudioPlatform}
              studioLanguage={studioLanguage}
              setStudioLanguage={setStudioLanguage}
              studioTopic={studioTopic}
              setStudioTopic={setStudioTopic}
              generatedVariations={generatedVariations}
              videoScript={videoScript}
              actionLoading={actionLoading}
              onGenerateVariations={handleGenerateVariations}
              onLaunchFullSuite={handleLaunchFullSuite}
              showToast={showToast}
              lessons={lessons}
              competitors={competitors}
            />
          )}

          {/* 3. REVIEW CENTER VIEW */}
          {activeTab === 'review' && (
            <ReviewCenterView
              queue={queue}
              reviewFilter={reviewFilter}
              setReviewFilter={setReviewFilter}
              onApprove={handleApprove}
              onOpenReject={handleOpenReject}
              onOpenEdit={handleOpenEdit}
              onRewrite={handleRewrite}
              onRegenerate={handleRegenerate}
              onOpenScheduleModal={handleOpenScheduleModal}
              actionLoading={actionLoading}
              getBrandBadge={getBrandBadge}
              getStatusBadge={getStatusBadge}
            />
          )}

          {/* 4. COMPETITOR INTEL VIEW */}
          {activeTab === 'competitors' && (
            <CompetitorIntelView
              competitors={competitors}
              scrapeUrlInput={scrapeUrlInput}
              setScrapeUrlInput={setScrapeUrlInput}
              scrapeBrand={scrapeBrand}
              setScrapeBrand={setScrapeBrand}
              scrapeResult={scrapeResult}
              actionLoading={actionLoading}
              onScrape={handleScrape}
              getSourceTypeBadge={getSourceTypeBadge}
            />
          )}

          {/* 5. LEADS VIEW */}
          {activeTab === 'leads' && (
            <LeadsView
              leads={leads}
              leadCountry={leadCountry}
              setLeadCountry={setLeadCountry}
              leadBrand={leadBrand}
              setLeadBrand={setLeadBrand}
              leadIndustry={leadIndustry}
              setLeadIndustry={setLeadIndustry}
              onDiscoverLeads={handleDiscoverLeadsWithFilters}
              onOpenEnrichModal={(lead) => {
                setEnrichModalLead(lead);
                setEnrichUrlInput('');
              }}
              actionLoading={actionLoading}
              showToast={showToast}
              getSourceTypeBadge={getSourceTypeBadge}
              getBrandBadge={getBrandBadge}
            />
          )}

          {/* 5b. PUBLISHING VIEW (Real LinkedIn Dispatch -- Project 2 "The Hands") */}
          {activeTab === 'publishing' && (
            <PublishingView
              queue={queue}
              publishingRecords={publishingRecords}
              actionLoading={actionLoading}
              onPublishToLinkedIn={handlePublishToLinkedIn}
              onRefreshEngagement={handleRefreshEngagement}
              onRunWorkerOnce={handleRunWorkerOnce}
              onCancelPublishing={handleCancelPublishing}
              getBrandBadge={getBrandBadge}
            />
          )}

          {/* 6. CLOSED-LOOP LEARNING VIEW */}
          {activeTab === 'learning' && (
            <LearningView
              lessons={lessons}
              feedbacks={feedbacks}
              onToggleLesson={handleToggleLesson}
            />
          )}

          {/* 7. ANALYTICS VIEW */}
          {activeTab === 'analytics' && (
            <AnalyticsView
              summary={summary}
              feedbacks={feedbacks}
            />
          )}
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-800/80 py-4 text-center text-xs text-slate-500 font-mono">
          JA Assure AI Marketing Command Center • Autonomous InsurTech Governance Platform
        </footer>
      </div>

      {/* Global Modals */}
      <Modals
        publishingModalItem={publishingModalItem}
        setPublishingModalItem={setPublishingModalItem}
        scheduledPlatform={scheduledPlatform}
        setScheduledPlatform={setScheduledPlatform}
        scheduledTime={scheduledTime}
        setScheduledTime={setScheduledTime}
        onConfirmSchedule={handleConfirmSchedule}

        rejectModalItem={rejectModalItem}
        setRejectModalItem={setRejectModalItem}
        rejectReasonTag={rejectReasonTag}
        setRejectReasonTag={setRejectReasonTag}
        rejectNotes={rejectNotes}
        setRejectNotes={setRejectNotes}
        onConfirmReject={handleConfirmReject}

        editModalItem={editModalItem}
        setEditModalItem={setEditModalItem}
        editContentText={editContentText}
        setEditContentText={setEditContentText}
        onConfirmEdit={handleConfirmEdit}

        enrichModalLead={enrichModalLead}
        setEnrichModalLead={setEnrichModalLead}
        enrichUrlInput={enrichUrlInput}
        setEnrichUrlInput={setEnrichUrlInput}
        onEnrichLead={handleEnrichLead}

        actionLoading={actionLoading}
        getBrandBadge={getBrandBadge}
      />
    </div>
  );
}

export default App;
