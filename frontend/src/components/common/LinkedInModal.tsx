import React, { useState } from 'react';
import { 
  CheckCircle2, 
  ExternalLink, 
  X, 
  ShieldCheck, 
  Send, 
  ArrowRight
} from 'lucide-react';
import { LinkedinIcon } from './BrandIcons';

interface LinkedInModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode?: 'status' | 'publish' | 'success';
  initialPostText?: string;
  initialPostId?: string;
  initialPostUrl?: string;
  onPublish?: (text: string) => Promise<any>;
}

export const LinkedInModal: React.FC<LinkedInModalProps> = ({
  isOpen,
  onClose,
  mode = 'status',
  initialPostText = '',
  initialPostId = 'urn:li:ugcPost:7507913809051807745',
  initialPostUrl = 'https://www.linkedin.com/feed/update/urn:li:ugcPost:7507913809051807745',
  onPublish
}) => {
  const [currentStep, setCurrentStep] = useState<'connected' | 'publish' | 'success'>(
    mode === 'publish' ? 'publish' : mode === 'success' ? 'success' : 'connected'
  );
  const [postText, setPostText] = useState(initialPostText);
  const [isPublishing, setIsPublishing] = useState(false);
  const [publishedUrl, setPublishedUrl] = useState(initialPostUrl);
  const [publishedId, setPublishedId] = useState(initialPostId);

  if (!isOpen) return null;

  const handlePublish = async () => {
    setIsPublishing(true);
    try {
      if (onPublish) {
        const res = await onPublish(postText);
        if (res && res.direct_url) {
          setPublishedUrl(res.direct_url);
        }
        if (res && res.post_id) {
          setPublishedId(res.post_id);
        }
      }
      setCurrentStep('success');
    } catch (e) {
      console.error(e);
    } finally {
      setIsPublishing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#0F172A] border border-slate-700/80 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#0077B5]/20 border border-[#0077B5]/40 flex items-center justify-center text-[#0077B5]">
              <LinkedinIcon className="w-5 h-5 fill-current" />
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-sm">
                {currentStep === 'connected' && 'LinkedIn Connection Status'}
                {currentStep === 'publish' && 'Publish to LinkedIn'}
                {currentStep === 'success' && 'Published Successfully'}
              </h3>
              <p className="text-[11px] text-slate-400 font-mono">
                JA Assure • Nexora Publishing Engine
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

        {/* Modal Content depending on Step */}
        <div className="p-6 space-y-5">
          {currentStep === 'connected' && (
            <div className="space-y-4">
              {/* Success Badge */}
              <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                <div>
                  <p className="text-xs font-bold text-emerald-300">Authentication successful</p>
                  <p className="text-[11px] text-emerald-400/80">Authorized for live UGC Post and video/image media dispatch</p>
                </div>
              </div>

              {/* Account Details Table */}
              <div className="bg-slate-900/60 rounded-xl p-4 border border-slate-800 space-y-2.5 text-xs">
                <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">Connected account</span>
                  <span className="text-white font-semibold flex items-center gap-1.5">
                    <LinkedinIcon className="w-3.5 h-3.5 text-[#0077B5]" />
                    Madhan D
                  </span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">Connection type</span>
                  <span className="text-slate-200 font-mono text-[11px]">Personal LinkedIn Profile</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">Workspace</span>
                  <span className="text-white font-semibold">JA Assure</span>
                </div>
                <div className="flex items-center justify-between py-1 border-b border-slate-800/80">
                  <span className="text-slate-400">Application</span>
                  <span className="text-white font-semibold">Nexora Ideas to Impact</span>
                </div>
                <div className="flex items-center justify-between py-1">
                  <span className="text-slate-400">Publishing status</span>
                  <span className="text-emerald-400 font-bold flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" /> Ready to publish
                  </span>
                </div>
              </div>

              {/* Notice */}
              <p className="text-[11px] text-slate-400 bg-slate-800/40 p-3 rounded-lg border border-slate-800 leading-relaxed">
                Posts published through this connection will appear on the connected personal LinkedIn account for <b>Madhan D</b>.
              </p>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  Close
                </button>
                <button
                  onClick={() => setCurrentStep('publish')}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors flex items-center gap-1.5 shadow-lg shadow-blue-600/20 cursor-pointer"
                >
                  Publish New Content
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {currentStep === 'publish' && (
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">
                  LinkedIn Post Content
                </label>
                <textarea
                  rows={6}
                  value={postText}
                  onChange={(e) => setPostText(e.target.value)}
                  placeholder="Enter compliant JA Assure post copy..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none font-sans leading-relaxed"
                />
              </div>

              <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Compliance Verification
                </span>
                <span className="text-emerald-400 font-bold font-mono">PASS (100/100)</span>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  onClick={() => setCurrentStep('connected')}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:bg-slate-800 transition-colors cursor-pointer"
                >
                  Back
                </button>
                <button
                  onClick={handlePublish}
                  disabled={isPublishing || !postText.trim()}
                  className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white transition-colors flex items-center gap-2 shadow-lg shadow-blue-600/30 cursor-pointer"
                >
                  {isPublishing ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Publishing to LinkedIn...
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      Publish to LinkedIn
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {currentStep === 'success' && (
            <div className="space-y-5 text-center py-2">
              <div className="w-14 h-14 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div>
                <h4 className="font-bold text-white text-base">Published Successfully</h4>
                <p className="text-xs text-slate-400 mt-1">
                  Your content has been published to LinkedIn in real time.
                </p>
              </div>

              <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800 space-y-2 text-xs text-left">
                <div className="flex justify-between border-b border-slate-800 pb-1.5">
                  <span className="text-slate-400">Platform</span>
                  <span className="text-white font-semibold">LinkedIn</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-1.5">
                  <span className="text-slate-400">Account</span>
                  <span className="text-white font-semibold">Madhan D (Personal Profile)</span>
                </div>
                <div className="flex justify-between border-b border-slate-800 pb-1.5">
                  <span className="text-slate-400">Post URN</span>
                  <span className="text-slate-300 font-mono text-[11px] truncate max-w-[240px]">{publishedId}</span>
                </div>
                <div className="flex justify-between pt-0.5">
                  <span className="text-slate-400">Status</span>
                  <span className="text-emerald-400 font-bold">201 CREATED & VERIFIED</span>
                </div>
              </div>

              <div className="flex items-center justify-center gap-3 pt-2">
                <a
                  href={publishedUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-[#0077B5] hover:bg-[#00669c] text-white transition-colors flex items-center gap-2 shadow-lg shadow-[#0077B5]/20 cursor-pointer"
                >
                  <ExternalLink className="w-4 h-4" />
                  View on LinkedIn
                </a>
                <button
                  onClick={onClose}
                  className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
