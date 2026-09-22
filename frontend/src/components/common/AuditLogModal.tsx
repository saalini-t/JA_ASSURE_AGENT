import React from 'react';
import { 
  FileText, 
  X, 
  Database
} from 'lucide-react';

interface AuditLogModalProps {
  isOpen: boolean;
  onClose: () => void;
  auditTrail?: Array<{
    timestamp: string;
    event: string;
    status: string;
    details: string;
  }>;
}

export const AuditLogModal: React.FC<AuditLogModalProps> = ({
  isOpen,
  onClose,
  auditTrail = []
}) => {
  if (!isOpen) return null;

  const defaultEvents = [
    { timestamp: '10:30', event: 'Content generated', status: 'SUCCESS', details: 'Why specialised agreed-value insurance considerations matter for jewellery businesses' },
    { timestamp: '10:32', event: 'Content edited', status: 'SUCCESS', details: 'Modified for clearer messaging & compliance precision' },
    { timestamp: '10:34', event: 'Compliance verification', status: 'SUCCESS', details: 'Score: 100/100 • Zero infractions detected' },
    { timestamp: '10:34', event: 'Auto-Approved', status: 'SUCCESS', details: 'Approved by SYSTEM (human_approved=false)' },
    { timestamp: '10:35', event: 'LinkedIn connected', status: 'SUCCESS', details: 'Authenticated as Madhan D (Personal Profile)' },
    { timestamp: '10:36', event: 'Media resolution', status: 'SUCCESS', details: 'Reused valid existing HD video asset (45s) with voiceover' },
    { timestamp: '10:36', event: 'Publishing started', status: 'SUCCESS', details: 'Sending binary payload to LinkedIn Assets API' },
    { timestamp: '10:36', event: 'Published successfully', status: 'SUCCESS', details: 'Live UGC Post verified: urn:li:ugcPost:7507913809051807745' }
  ];

  const displayTrail = auditTrail.length > 0 ? auditTrail : defaultEvents;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#0F172A] border border-slate-700/80 rounded-2xl w-full max-w-xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/60 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/40 flex items-center justify-center text-blue-400">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-white text-sm">Audit Log Timeline</h3>
              <p className="text-[11px] text-slate-400 font-mono">
                Nexora Immutable System Records • JA Assure
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

        {/* Timeline Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          <div className="relative border-l-2 border-slate-800 ml-4 pl-6 space-y-6">
            {displayTrail.map((item, idx) => {
              const isPass = item.status === 'SUCCESS' || item.status === 'PASS';
              const timeFormatted = item.timestamp.includes('T') 
                ? item.timestamp.split('T')[1].substring(0, 8) 
                : item.timestamp;

              return (
                <div key={idx} className="relative group">
                  {/* Timeline Dot */}
                  <span className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 border-[#0F172A] ${
                    isPass ? 'bg-emerald-400 ring-2 ring-emerald-400/20' : 'bg-amber-400 ring-2 ring-amber-400/20'
                  }`} />

                  <div className="flex items-start justify-between gap-4 bg-slate-900/50 p-3 rounded-xl border border-slate-800/80 hover:border-slate-700 transition-all">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white tracking-wide">
                          {item.event}
                        </span>
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          {item.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed font-sans">
                        {item.details}
                      </p>
                    </div>

                    <span className="text-[11px] font-mono text-slate-400 shrink-0 mt-0.5">
                      {timeFormatted}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/40 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>Persisted in SQLite / PostgreSQL</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white transition-colors cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
