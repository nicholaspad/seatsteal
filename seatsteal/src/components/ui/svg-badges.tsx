import * as React from "react";

interface BadgeSvgProps extends React.SVGProps<SVGSVGElement> {
  className?: string;
}

export function PlusBadgeSvg({ className, ...props }: BadgeSvgProps) {
  return (
    <svg
      width="52"
      height="24"
      viewBox="0 0 52 24"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient id="plusGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#1e3a8a" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="52" height="24" rx="6" ry="6" fill="url(#plusGradient)" />
      <text
        x="26"
        y="16"
        textAnchor="middle"
        fill="white"
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="12"
        fontWeight="700"
      >
        Plus
      </text>
    </svg>
  );
}

export function ProBadgeSvg({ className, ...props }: BadgeSvgProps) {
  return (
    <svg
      width="46"
      height="24"
      viewBox="0 0 46 24"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient id="proBorderGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#a855f7" />
          <stop offset="100%" stopColor="#ef4444" />
        </linearGradient>
        <linearGradient id="proFillGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#a855f7" />
          <stop offset="100%" stopColor="#ec4899" />
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="46" height="24" rx="6" ry="6" fill="url(#proBorderGradient)" />
      <rect x="2" y="2" width="42" height="20" rx="4" ry="4" fill="url(#proFillGradient)" />
      <text
        x="23"
        y="16"
        textAnchor="middle"
        fill="white"
        fontFamily="system-ui, -apple-system, sans-serif"
        fontSize="12"
        fontWeight="700"
      >
        Pro
      </text>
    </svg>
  );
}
