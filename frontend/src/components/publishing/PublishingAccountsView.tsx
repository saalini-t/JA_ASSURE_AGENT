import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  Sparkles
} from 'lucide-react';
import { LinkedinIcon, InstagramIcon, XTwitterIcon } from '../common/BrandIcons';

interface PublishingAccountsViewProps {
  onOpenLinkedInModal: () => void;
}

export const PublishingAccountsView: React.FC<PublishingAccountsViewProps> = ({ onOpenLinkedInModal }) => {
  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-300">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Connect Publishing Accounts</h2>
        <p className="text-xs text-slate-400 mt-1">
          Connect JA Assure's authorized social publishing accounts to Nexora.
        </p>
      </div>

      {/* Account Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        {/* 1. LinkedIn Card — CONNECTED (Live) */}
        <div className="bg-[#0F172A] border-2 border-blue-500/40 rounded-2xl p-5 space-y-4 shadow-xl shadow-blue-500/5 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full blur-2xl pointer-events-none" />
          
          <div className="w-12 h-12 rounded-xl bg-[#0077B5]/20 border border-[#0077B5]/40 flex items-center justify-center text-[#0077B5] shadow-md">
            <LinkedinIcon className="w-6 h-6 fill-current" />
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">JA Assure LinkedIn</h3>
            <div className="flex items-center gap-1.5 mt-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-400">Connected</span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono mt-1">
              Madhan D — Personal LinkedIn
            </p>
          </div>

          <div className="pt-2">
            <button
              onClick={onOpenLinkedInModal}
              className="w-full py-2.5 rounded-xl text-xs font-semibold bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 transition-colors flex items-center justify-center gap-2 cursor-pointer"
            >
              Manage & Publish
            </button>
          </div>
        </div>

        {/* 2. Instagram Card — Not Connected */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg">
          <div className="w-12 h-12 rounded-xl bg-pink-500/10 border border-pink-500/30 flex items-center justify-center text-pink-400 shadow-md">
            <InstagramIcon className="w-6 h-6" />
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">JA Assure Instagram</h3>
            <div className="flex items-center gap-1.5 mt-1">
              <XCircle className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-semibold text-slate-500">Not connected</span>
            </div>
            <p className="text-[11px] text-slate-500 font-mono mt-1">
              Connect Carousel & Reels Publishing
            </p>
          </div>

          <div className="pt-2">
            <button
              disabled
              className="w-full py-2.5 rounded-xl text-xs font-semibold bg-slate-800/60 text-slate-400 border border-slate-700/50 cursor-not-allowed transition-colors"
            >
              Connect Instagram
            </button>
          </div>
        </div>

        {/* 3. X Card — Not Connected */}
        <div className="bg-[#0F172A] border border-slate-800 rounded-2xl p-5 space-y-4 shadow-lg">
          <div className="w-12 h-12 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-200 shadow-md">
            <XTwitterIcon className="w-6 h-6" />
          </div>

          <div>
            <h3 className="font-bold text-white text-sm">JA Assure X</h3>
            <div className="flex items-center gap-1.5 mt-1">
              <XCircle className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-semibold text-slate-500">Not connected</span>
            </div>
            <p className="text-[11px] text-slate-500 font-mono mt-1">
              Connect Thread & Post Publishing
            </p>
          </div>

          <div className="pt-2">
            <button
              disabled
              className="w-full py-2.5 rounded-xl text-xs font-semibold bg-slate-800/60 text-slate-400 border border-slate-700/50 cursor-not-allowed transition-colors"
            >
              Connect X
            </button>
          </div>
        </div>

      </div>

      {/* Information Banner */}
      <div className="p-4 rounded-xl bg-blue-950/20 border border-blue-800/40 text-xs text-blue-300 flex items-start gap-3">
        <Sparkles className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
        <p className="leading-relaxed">
          For this phase, you can connect and publish directly via personal accounts for testing. To publish on official JA Assure pages, authorized company page OAuth access will be required.
        </p>
      </div>
    </div>
  );
};
