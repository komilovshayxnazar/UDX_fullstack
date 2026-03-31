import React from 'react';

interface AppIconProps {
  size?: number;
  className?: string;
}

export function AppIcon({ size = 512, className = '' }: AppIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Background Circle */}
      <circle cx="256" cy="256" r="256" fill="#af47ff" />
      
      {/* Wheat/Grain stalk on left */}
      <path
        d="M160 380 L160 200 
           M140 220 Q140 210, 150 210 Q160 210, 160 220 
           M140 240 Q140 230, 150 230 Q160 230, 160 240 
           M140 260 Q140 250, 150 250 Q160 250, 160 260 
           M140 280 Q140 270, 150 270 Q160 270, 160 280 
           M140 300 Q140 290, 150 290 Q160 290, 160 300"
        stroke="white"
        strokeWidth="8"
        strokeLinecap="round"
        fill="none"
      />
      
      {/* Wheat/Grain stalk on right */}
      <path
        d="M180 220 Q180 210, 170 210 Q160 210, 160 220 
           M180 240 Q180 230, 170 230 Q160 230, 160 240 
           M180 260 Q180 250, 170 250 Q160 250, 160 260 
           M180 280 Q180 270, 170 270 Q160 270, 160 280 
           M180 300 Q180 290, 170 290 Q160 290, 160 300"
        stroke="white"
        strokeWidth="8"
        strokeLinecap="round"
        fill="none"
      />
      
      {/* Shopping Cart */}
      <g transform="translate(240, 180)">
        {/* Cart body */}
        <path
          d="M10 30 L30 30 L50 120 L120 120"
          stroke="white"
          strokeWidth="12"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <path
          d="M50 120 L120 120 L110 180 L60 180 Z"
          fill="white"
          stroke="white"
          strokeWidth="8"
          strokeLinejoin="round"
        />
        
        {/* Cart wheels */}
        <circle cx="70" cy="200" r="12" fill="white" />
        <circle cx="110" cy="200" r="12" fill="white" />
        
        {/* Cart top lines */}
        <line x1="55" y1="120" x2="60" y2="160" stroke="#af47ff" strokeWidth="8" strokeLinecap="round" />
        <line x1="75" y1="120" x2="75" y2="165" stroke="#af47ff" strokeWidth="8" strokeLinecap="round" />
        <line x1="95" y1="120" x2="90" y2="165" stroke="#af47ff" strokeWidth="8" strokeLinecap="round" />
      </g>
      
      {/* Letter "U" integrated into design */}
      <path
        d="M140 140 L140 100 Q140 70, 170 70 Q200 70, 200 100 L200 140"
        stroke="white"
        strokeWidth="16"
        strokeLinecap="round"
        fill="none"
        opacity="0.4"
      />
      
      {/* Connecting element - represents exchange/marketplace */}
      <path
        d="M210 260 L240 260 M220 250 L230 260 L220 270"
        stroke="rgba(255,255,255,0.6)"
        strokeWidth="10"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

// For favicon generation
export function generateFaviconSVG(): string {
  return `<svg width="512" height="512" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="256" cy="256" r="256" fill="#af47ff"/>
  <path d="M160 380 L160 200 M140 220 Q140 210, 150 210 Q160 210, 160 220 M140 240 Q140 230, 150 230 Q160 230, 160 240 M140 260 Q140 250, 150 250 Q160 250, 160 260 M140 280 Q140 270, 150 270 Q160 270, 160 280 M140 300 Q140 290, 150 290 Q160 290, 160 300" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
  <path d="M180 220 Q180 210, 170 210 Q160 210, 160 220 M180 240 Q180 230, 170 230 Q160 230, 160 240 M180 260 Q180 250, 170 250 Q160 250, 160 260 M180 280 Q180 270, 170 270 Q160 270, 160 280 M180 300 Q180 290, 170 290 Q160 290, 160 300" stroke="white" stroke-width="8" stroke-linecap="round" fill="none"/>
  <g transform="translate(240, 180)">
    <path d="M10 30 L30 30 L50 120 L120 120" stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <path d="M50 120 L120 120 L110 180 L60 180 Z" fill="white" stroke="white" stroke-width="8" stroke-linejoin="round"/>
    <circle cx="70" cy="200" r="12" fill="white"/>
    <circle cx="110" cy="200" r="12" fill="white"/>
    <line x1="55" y1="120" x2="60" y2="160" stroke="#af47ff" stroke-width="8" stroke-linecap="round"/>
    <line x1="75" y1="120" x2="75" y2="165" stroke="#af47ff" stroke-width="8" stroke-linecap="round"/>
    <line x1="95" y1="120" x2="90" y2="165" stroke="#af47ff" stroke-width="8" stroke-linecap="round"/>
  </g>
  <path d="M140 140 L140 100 Q140 70, 170 70 Q200 70, 200 100 L200 140" stroke="white" stroke-width="16" stroke-linecap="round" fill="none" opacity="0.4"/>
  <path d="M210 260 L240 260 M220 250 L230 260 L220 270" stroke="rgba(255,255,255,0.6)" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>`;
}
