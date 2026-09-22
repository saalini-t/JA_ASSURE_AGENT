import React from 'react';

interface NexoraLogoProps {
  size?: 'sm' | 'md' | 'lg';
  showTagline?: boolean;
}

export const NexoraLogo: React.FC<NexoraLogoProps> = ({ size = 'md', showTagline = true }) => {
  const iconSizes = {
    sm: 'w-7 h-7',
    md: 'w-9 h-9',
    lg: 'w-12 h-12'
  };

  const textSizes = {
    sm: 'text-base',
    md: 'text-xl',
    lg: 'text-2xl'
  };

  return (
    <div className="flex items-center gap-3 select-none">
      {/* Dynamic Ribbon Gradient 'N' Icon with Sparkle Star */}
      <div className={`relative ${iconSizes[size]} flex items-center justify-center shrink-0`}>
        <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full drop-shadow-md">
          <defs>
            <linearGradient id="nexoraRibbon1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#2563EB" />
              <stop offset="50%" stopColor="#0EA5E9" />
              <stop offset="100%" stopColor="#10B981" />
            </linearGradient>
            <linearGradient id="nexoraRibbon2" x1="100%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#10B981" />
              <stop offset="50%" stopColor="#06B6D4" />
              <stop offset="100%" stopColor="#3B82F6" />
            </linearGradient>
          </defs>
          {/* Continuous Ribbon Curve */}
          <path
            d="M22 76C18 64 26 30 44 32C56 34 50 68 64 68C76 68 84 40 84 24C84 38 72 78 52 76C36 74 42 42 28 44C20 46 22 66 22 76Z"
            fill="url(#nexoraRibbon1)"
          />
          {/* Leaf / Wing overlap */}
          <path
            d="M52 48C58 32 72 20 86 16C84 32 74 48 60 56C54 52 52 48 52 48Z"
            fill="url(#nexoraRibbon2)"
          />
          {/* Sparkle Star */}
          <path
            d="M86 12C87 8 89 6 93 5C89 4 87 2 86 -2C85 2 83 4 79 5C83 6 85 8 86 12Z"
            fill="#34D399"
          />
        </svg>
      </div>

      <div className="flex flex-col">
        <div className="flex items-center gap-1.5">
          <span className={`font-extrabold ${textSizes[size]} tracking-tight text-white font-sans`}>
            Nexora
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
        </div>
        {showTagline && (
          <span className="text-[10px] tracking-widest text-slate-400 font-medium uppercase font-mono -mt-0.5">
            Ideas to Impact
          </span>
        )}
      </div>
    </div>
  );
};
