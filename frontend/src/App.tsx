import { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  AlertCircle
} from 'lucide-react';
import { api, API_ORIGIN } from './services/api';
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
import { PublishingAccountsView } from './components/publishing/PublishingAccountsView';
import { LearningView } from './components/learning/LearningView';
import { Modals } from './components/common/Modals';
import { LinkedInModal } from './components/common/LinkedInModal';
import { AuditLogModal } from './components/common/AuditLogModal';
import { AutonomousRunnerModal } from './components/common/AutonomousRunnerModal';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'studio' | 'library' | 'review' | 'publishing' | 'learning' | 'competitors' | 'leads' | 'analytics'>('dashboard');
  const [selectedBrand, setSelectedBrand] = useState<string>('all');
  
  // Data states
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [queue, setQueue] = useState<ContentQueueItem[]>([]);
  const [lessons, setLessons] = useState<LessonLearned[]>([]);
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([]);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [_leads, setLeads] = useState<Lead[]>([]);
  const [_publishingRecords, setPublishingRecords] = useState<PublishingRecord[]>([]);
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Studio Form states
  const [studioBrand, setStudioBrand] = useState<'jade' | 'doctorshield' | 'jaguartransit'>('jade');
  const [studioPlatform, setStudioPlatform] = useState<string>('linkedin');
  const [studioLanguage, setStudioLanguage] = useState<string>('en');
  const [studioTopic, setStudioTopic] = useState<string>('Why specialised agreed-value insurance considerations matter for jewellery businesses');
  const [generatedVariations, setGeneratedVariations] = useState<GeneratedVariation[]>([]);
  const [videoScript, setVideoScript] = useState<VideoScript | null>(null);

  // Review & Modals
  const [reviewFilter, setReviewFilter] = useState<'pending' | 'approved' | 'rejected' | 'all'>('pending');
  const [publishingModalItem, setPublishingModalItem] = useState<ContentQueueItem | null>(null);
  const [scheduledPlatform, setScheduledPlatform] = useState<string>('linkedin');
  const [scheduledTime, setScheduledTime] = useState<string>('');
  
  const [rejectModalItem, setRejectModalItem] = useState<ContentQueueItem | null>(null);
  const [rejectReasonTag, setRejectReasonTag] = useState<string>('false_guarantee');
  const [rejectNotes, setRejectNotes] = useState<string>('');
  
  const [editModalItem, setEditModalItem] = useState<ContentQueueItem | null>(null);
  const [editContentText, setEditContentText] = useState<string>('');

  const [enrichModalLead, setEnrichModalLead] = useState<Lead | null>(null);
  const [enrichUrlInput, setEnrichUrlInput] = useState<string>('');

  // Specialized Nexora Modals
  const [isLinkedInModalOpen, setIsLinkedInModalOpen] = useState(false);
  const [linkedInModalMode, setLinkedInModalMode] = useState<'status' | 'publish' | 'success'>('status');
  const [isAuditLogOpen, setIsAuditLogOpen] = useState(false);
  const [isAutonomousModalOpen, setIsAutonomousModalOpen] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const getBrandBadge = (brand: string) => {
    switch (brand.toLowerCase()) {
      case 'jade':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            JADE
          </span>
        );
      case 'doctorshield':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-blue-500/15 text-blue-400 border border-blue-500/30">
            DOCTORSHIELD
          </span>
        );
      case 'jaguartransit':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-amber-500/15 text-amber-400 border border-amber-500/30">
            JAGUARTRANSIT
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-slate-500/15 text-slate-300 border border-slate-500/30">
            {brand.toUpperCase()}
          </span>
        );
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'published':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            Published
          </span>
        );
      case 'approved':
      case 'auto_approved':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            Approved
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            Rejected
          </span>
        );
      case 'pending':
      case 'human_review':
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            Pending Review
          </span>
        );
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [h, s, q, les, fb, pubs, comp, ld] = await Promise.all([
        api.getHealth(),
        api.getDashboardSummary(),
        api.getQueue({ brand: selectedBrand !== 'all' ? selectedBrand : undefined }),
        api.getLessons(),
        api.getFeedback(),
        api.getPublishingRecords(),
        api.getCompetitors(),
        api.getLeads()
      ]);
      setHealth(h);
      setSummary(s);
      setQueue(q);
      setLessons(les);
      setFeedbacks(fb);
      setPublishingRecords(pubs);
      setCompetitors(comp);
      setLeads(ld);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Nexora Backend unavailable at http://localhost:8000.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllData();
  }, [selectedBrand]);

  const handleApprove = async (id: number) => {
    setActionLoading(`approve-${id}`);
    try {
      await api.approveContent(id);
      showToast(`Content #${id} approved!`);
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleConfirmReject = async () => {
    if (!rejectModalItem) return;
    setActionLoading('rejecting');
    try {
      await api.rejectContent(rejectModalItem.id, rejectReasonTag, rejectNotes);
      showToast(`Content #${rejectModalItem.id} rejected. Feedback recorded.`);
      setRejectModalItem(null);
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleConfirmEdit = async () => {
    if (!editModalItem) return;
    setActionLoading('editing');
    try {
      await api.editContent(editModalItem.id, editContentText);
      showToast(`Content #${editModalItem.id} edited and approved.`);
      setEditModalItem(null);
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRewrite = async (id: number) => {
    setActionLoading(`rewrite-${id}`);
    try {
      await api.rewriteContent(id);
      showToast(`Content #${id} auto-corrected & rewritten.`);
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRegenerate = async (id: number) => {
    setActionLoading(`regen-${id}`);
    try {
      await api.regenerateContent(id);
      showToast(`Content #${id} fully regenerated.`);
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleConfirmSchedule = async () => {
    if (!publishingModalItem) return;
    setActionLoading('scheduling');
    try {
      await api.schedulePublishing({
        content_id: publishingModalItem.id,
        platform: scheduledPlatform,
        scheduled_at: scheduledTime || undefined
      });
      showToast(`Content #${publishingModalItem.id} scheduled for ${scheduledPlatform.toUpperCase()}`);
      setPublishingModalItem(null);
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleEnrichLead = async () => {
    if (!enrichModalLead) return;
    setActionLoading('enriching-lead');
    try {
      await api.enrichLead(enrichModalLead.id, enrichUrlInput || undefined);
      showToast(`Lead "${enrichModalLead.company}" enriched successfully.`);
      setEnrichModalLead(null);
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleLesson = async (lessonId: number) => {
    try {
      await api.toggleLesson(lessonId);
      showToast('Learning rule updated.');
      fetchAllData();
    } catch (err: any) {
      showToast(`Error: ${err.message}`);
    }
  };

  const handleGenerateVariations = async () => {
    setActionLoading('generating-variations');
    try {
      if (studioPlatform === 'reel' || studioPlatform === 'video') {
        const script = await api.generateVideoScript({
          brand: studioBrand,
          topic: studioTopic,
          platform: studioPlatform,
          language: studioLanguage
        });
        setVideoScript(script);
        setGeneratedVariations([]);
        showToast(`Generated ${studioPlatform.toUpperCase()} storyboard for ${studioBrand.toUpperCase()}`);
      } else {
        setVideoScript(null);
        const vars = await api.generateVariations({
          brand: studioBrand,
          platform: studioPlatform,
          topic: studioTopic,
          language: studioLanguage
        });
        setGeneratedVariations(vars);
        showToast(`Generated ${vars.length} variations for ${studioBrand.toUpperCase()}`);
      }
    } catch (err: any) {
      showToast(`Generation Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleLaunchFullSuite = async () => {
    setActionLoading('generating-suite');
    try {
      const items = await api.generateSuite({
        brand: studioBrand,
        topic: studioTopic,
        platforms: ['linkedin', 'instagram', 'x'],
        content_types: ['social_post', 'carousel', 'video'],
        languages: ['en']
      });
      showToast(`Suite generated! ${items.length} items added to Review Queue.`);
      fetchAllData();
    } catch (err: any) {
      showToast(`Suite Error: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handlePublishDirect = async (text: string) => {
    const res = await fetch(`${API_ORIGIN}/api/v1/publishing/linkedin/dispatch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        title: 'JA Assure Content Publication',
        dry_run: false
      })
    });
    const data = await res.json();
    showToast('LinkedIn publication successful!');
    fetchAllData();
    return data;
  };

  const pendingReviewItems = queue.filter(
    (q) => q.status === 'pending' || q.status === 'human_review' || (q.status === 'approved' && q.compliance_status === 'flagged')
  );

  return (
    <div className="flex h-screen bg-[#070C16] text-slate-100 font-sans overflow-hidden">
      {/* Modern Nexora Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        pendingReviewCount={pendingReviewItems.length}
        health={health}
        onOpenAuditLog={() => setIsAuditLogOpen(true)}
        onOpenLinkedInModal={() => {
          setLinkedInModalMode('status');
          setIsLinkedInModalOpen(true);
        }}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header
          activeTab={activeTab as any}
          selectedBrand={selectedBrand}
          setSelectedBrand={setSelectedBrand}
          health={health}
          loading={loading}
          onRefresh={fetchAllData}
        />

        {/* Global Error Banner */}
        {error && (
          <div className="bg-rose-500/10 border-b border-rose-500/20 px-6 py-2.5 flex items-center justify-between text-xs text-rose-300">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-rose-400" />
              <span>{error}</span>
            </div>
            <button 
              onClick={fetchAllData}
              className="text-[11px] underline hover:text-white font-medium"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* Toast Alert */}
        {toastMessage && (
          <div className="fixed top-5 right-5 z-50 p-4 rounded-xl bg-slate-900 border border-blue-500/40 text-white text-xs font-semibold shadow-2xl flex items-center gap-2 animate-in slide-in-from-top duration-200">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Tab Views */}
        <main className="flex-1 overflow-y-auto bg-[#0A101D] p-6">
          {activeTab === 'dashboard' && (
            <DashboardView
              summary={summary}
              queue={queue}
              onNavigate={(tab: string) => setActiveTab(tab as any)}
              onOpenLinkedInModal={() => {
                setLinkedInModalMode('status');
                setIsLinkedInModalOpen(true);
              }}
              onOpenAutonomousModal={() => setIsAutonomousModalOpen(true)}
              onOpenAuditLog={() => setIsAuditLogOpen(true)}
            />
          )}

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

          {activeTab === 'review' && (
            <ReviewCenterView
              queue={queue}
              reviewFilter={reviewFilter}
              setReviewFilter={setReviewFilter}
              onApprove={handleApprove}
              onOpenReject={(item) => {
                setRejectModalItem(item);
                setRejectNotes('');
              }}
              onOpenEdit={(item) => {
                setEditModalItem(item);
                setEditContentText(item.content_raw);
              }}
              onRewrite={handleRewrite}
              onRegenerate={handleRegenerate}
              onOpenScheduleModal={(item) => {
                setPublishingModalItem(item);
                setScheduledPlatform(item.platform || 'linkedin');
              }}
              actionLoading={actionLoading}
              getBrandBadge={getBrandBadge}
              getStatusBadge={getStatusBadge}
              onRefresh={fetchAllData}
              showToast={showToast}
            />
          )}

          {activeTab === 'library' && (
            <ReviewCenterView
              queue={queue}
              reviewFilter="all"
              setReviewFilter={setReviewFilter}
              onApprove={handleApprove}
              onOpenReject={(item) => {
                setRejectModalItem(item);
                setRejectNotes('');
              }}
              onOpenEdit={(item) => {
                setEditModalItem(item);
                setEditContentText(item.content_raw);
              }}
              onRewrite={handleRewrite}
              onRegenerate={handleRegenerate}
              onOpenScheduleModal={(item) => {
                setPublishingModalItem(item);
                setScheduledPlatform(item.platform || 'linkedin');
              }}
              actionLoading={actionLoading}
              getBrandBadge={getBrandBadge}
              getStatusBadge={getStatusBadge}
              onRefresh={fetchAllData}
              showToast={showToast}
            />
          )}

          {activeTab === 'publishing' && (
            <PublishingAccountsView
              onOpenLinkedInModal={() => {
                setLinkedInModalMode('status');
                setIsLinkedInModalOpen(true);
              }}
            />
          )}

          {activeTab === 'learning' && (
            <LearningView
              lessons={lessons}
              feedbacks={feedbacks}
              onToggleLesson={handleToggleLesson}
            />
          )}
        </main>
      </div>

      {/* Modals & Dialogs */}
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

      <LinkedInModal
        isOpen={isLinkedInModalOpen}
        onClose={() => setIsLinkedInModalOpen(false)}
        mode={linkedInModalMode}
        onPublish={handlePublishDirect}
      />

      <AuditLogModal
        isOpen={isAuditLogOpen}
        onClose={() => setIsAuditLogOpen(false)}
      />

      <AutonomousRunnerModal
        isOpen={isAutonomousModalOpen}
        onClose={() => setIsAutonomousModalOpen(false)}
        onCompleted={fetchAllData}
      />
    </div>
  );
}

export default App;
