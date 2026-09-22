import type {
  ContentQueueItem,
  Competitor,
  Lead,
  Feedback,
  LessonLearned,
  DashboardSummary,
  HealthCheckResponse,
  GeneratedVariation,
  VideoScript,
  ComplianceResult,
  PublishingRecord,
  ReviewDecisionItem,
  VoiceGenerationResponse
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Server origin (no /api/v1 suffix) for fetching static assets like generated videos,
// e.g. `${API_ORIGIN}/media/generated/{job_id}/final.mp4`.
export const API_ORIGIN = API_BASE_URL.replace(/\/api\/v1\/?$/, '');

// Convenience wrapper for turning any relative /media/... path (video, audio, srt)
// into a fully-qualified URL. Passes absolute URLs through unchanged.
export const getMediaUrl = (path?: string): string => {
  if (!path) return '';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  return `${API_ORIGIN}${path.startsWith('/') ? '' : '/'}${path}`;
};

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error ${res.status}: ${errorText || res.statusText}`);
  }
  return res.json();
}

export const api = {
  // System Health
  getHealth: async (): Promise<HealthCheckResponse> => {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse<HealthCheckResponse>(res);
  },

  // Analytics
  getDashboardSummary: async (): Promise<DashboardSummary> => {
    const res = await fetch(`${API_BASE_URL}/analytics/summary`);
    return handleResponse<DashboardSummary>(res);
  },

  // Content Queue & Human Review
  getQueue: async (params?: { brand?: string; platform?: string; status?: string; compliance_status?: string }): Promise<ContentQueueItem[]> => {
    const query = new URLSearchParams();
    if (params?.brand && params.brand !== 'all') query.append('brand', params.brand);
    if (params?.platform && params.platform !== 'all') query.append('platform', params.platform);
    if (params?.status && params.status !== 'all') query.append('status', params.status);
    if (params?.compliance_status && params.compliance_status !== 'all') query.append('compliance_status', params.compliance_status);
    const res = await fetch(`${API_BASE_URL}/queue?${query.toString()}`);
    return handleResponse<ContentQueueItem[]>(res);
  },

  getQueueItem: async (id: number): Promise<ContentQueueItem> => {
    const res = await fetch(`${API_BASE_URL}/queue/${id}`);
    return handleResponse<ContentQueueItem>(res);
  },

  approveContent: async (id: number, notes?: string): Promise<ContentQueueItem> => {
    const query = notes ? `?notes=${encodeURIComponent(notes)}` : '';
    const res = await fetch(`${API_BASE_URL}/queue/${id}/approve${query}`, { method: 'POST' });
    return handleResponse<ContentQueueItem>(res);
  },

  rejectContent: async (id: number, reasonTag: string, notes: string): Promise<ContentQueueItem> => {
    const res = await fetch(`${API_BASE_URL}/queue/${id}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason_tag: reasonTag, notes }),
    });
    return handleResponse<ContentQueueItem>(res);
  },

  editContent: async (id: number, editedContent: string, reasonTag?: string, notes?: string): Promise<ContentQueueItem> => {
    const res = await fetch(`${API_BASE_URL}/queue/${id}/edit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        edited_content: editedContent,
        reason_tag: reasonTag || 'human_edit',
        notes: notes || 'Edited and verified by reviewer'
      }),
    });
    return handleResponse<ContentQueueItem>(res);
  },

  rewriteContent: async (id: number): Promise<ContentQueueItem> => {
    const res = await fetch(`${API_BASE_URL}/queue/${id}/rewrite`, { method: 'POST' });
    return handleResponse<ContentQueueItem>(res);
  },

  regenerateContent: async (id: number): Promise<ContentQueueItem> => {
    const res = await fetch(`${API_BASE_URL}/queue/${id}/regenerate`, { method: 'POST' });
    return handleResponse<ContentQueueItem>(res);
  },

  getReviewHistory: async (id: number): Promise<ReviewDecisionItem[]> => {
    const res = await fetch(`${API_BASE_URL}/queue/${id}/history`);
    return handleResponse<ReviewDecisionItem[]>(res);
  },

  // Content Generation
  generateVariations: async (payload: {
    brand: string;
    platform: string;
    topic: string;
    content_type?: string;
    language?: string;
    key_benefits?: string[];
    target_persona?: string;
    cta?: string;
  }): Promise<GeneratedVariation[]> => {
    const res = await fetch(`${API_BASE_URL}/content/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<GeneratedVariation[]>(res);
  },

  generateSuite: async (payload: {
    brand: string;
    topic: string;
    platforms: string[];
    content_types: string[];
    languages: string[];
    key_benefits?: string[];
  }): Promise<ContentQueueItem[]> => {
    const res = await fetch(`${API_BASE_URL}/content/suite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<ContentQueueItem[]>(res);
  },

  generateVideoScript: async (payload: {
    brand: string;
    topic: string;
    target_duration?: number;
    platform?: string;
    language?: string;
    target_audience?: string;
  }): Promise<VideoScript> => {
    const res = await fetch(`${API_BASE_URL}/content/video`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<VideoScript>(res);
  },

  // Voice & TTS
  generateVoiceover: async (script: VideoScript, languageOverride?: string): Promise<VoiceGenerationResponse> => {
    let url = `${API_BASE_URL}/content/voice`;
    if (languageOverride) {
      url += `?language_override=${encodeURIComponent(languageOverride)}`;
    }
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(script),
    });
    return handleResponse<VoiceGenerationResponse>(res);
  },

  // Compliance
  checkCompliance: async (payload: { brand: string; content_text: string; content_type?: string }): Promise<ComplianceResult> => {
    const res = await fetch(`${API_BASE_URL}/compliance/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<ComplianceResult>(res);
  },

  // Competitor & Research
  getCompetitors: async (): Promise<Competitor[]> => {
    const res = await fetch(`${API_BASE_URL}/competitors`);
    return handleResponse<Competitor[]>(res);
  },

  runResearch: async (payload: { brand: string; topic: string; competitor_url?: string }): Promise<any> => {
    const res = await fetch(`${API_BASE_URL}/research/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  analyzeCompetitorUrl: async (url: string, brand?: string): Promise<Competitor> => {
    const res = await fetch(`${API_BASE_URL}/competitors/analyze-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, brand }),
    });
    return handleResponse<Competitor>(res);
  },

  scrapeUrl: async (url: string): Promise<any> => {
    const res = await fetch(`${API_BASE_URL}/research/scrape`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    return handleResponse<any>(res);
  },

  // Leads
  getLeads: async (params?: { industry?: string; status?: string }): Promise<Lead[]> => {
    const query = new URLSearchParams();
    if (params?.industry) query.append('industry', params.industry);
    if (params?.status) query.append('status', params.status);
    const res = await fetch(`${API_BASE_URL}/leads?${query.toString()}`);
    return handleResponse<Lead[]>(res);
  },

  discoverLeads: async (payload: {
    brand?: string;
    country?: string;
    industry?: string;
    target_audience?: string;
    keywords?: string;
  }): Promise<any> => {
    const res = await fetch(`${API_BASE_URL}/leads/discover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  enrichLead: async (leadId: number, sourceUrl?: string): Promise<Lead> => {
    const res = await fetch(`${API_BASE_URL}/leads/${leadId}/enrich`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_url: sourceUrl }),
    });
    return handleResponse<Lead>(res);
  },

  generateLeadOutreach: async (leadId: number): Promise<any> => {
    const res = await fetch(`${API_BASE_URL}/leads/${leadId}/outreach`, { method: 'POST' });
    return handleResponse<any>(res);
  },

  // Lessons Learned & Feedback
  getLessons: async (category?: string): Promise<LessonLearned[]> => {
    const query = category ? `?category=${category}` : '';
    const res = await fetch(`${API_BASE_URL}/lessons${query}`);
    return handleResponse<LessonLearned[]>(res);
  },

  toggleLesson: async (lessonId: number): Promise<LessonLearned> => {
    const res = await fetch(`${API_BASE_URL}/lessons/${lessonId}/toggle`, { method: 'PATCH' });
    return handleResponse<LessonLearned>(res);
  },

  getFeedback: async (): Promise<Feedback[]> => {
    const res = await fetch(`${API_BASE_URL}/feedback`);
    return handleResponse<Feedback[]>(res);
  },

  // Publishing (Simulated Dispatch Preview)
  getPublishingRecords: async (): Promise<PublishingRecord[]> => {
    const res = await fetch(`${API_BASE_URL}/publishing`);
    return handleResponse<PublishingRecord[]>(res);
  },

  schedulePublishing: async (payload: {
    content_id: number;
    platform?: string;
    scheduled_at?: string;
  }): Promise<PublishingRecord> => {
    const res = await fetch(`${API_BASE_URL}/publishing`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<PublishingRecord>(res);
  },

  // Direct LinkedIn Publishing Dispatch
  dispatchLinkedIn: async (payload: {
    text: string;
    item_id?: number;
    media_path?: string;
    media_type?: string;
    title?: string;
    dry_run?: boolean;
  }): Promise<any> => {
    const res = await fetch(`${API_BASE_URL}/publishing/linkedin/dispatch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<any>(res);
  },

  cancelPublishing: async (recordId: number): Promise<PublishingRecord> => {
    const res = await fetch(`${API_BASE_URL}/publishing/${recordId}/cancel`, {
      method: 'PATCH',
    });
    return handleResponse<PublishingRecord>(res);
  }
};
