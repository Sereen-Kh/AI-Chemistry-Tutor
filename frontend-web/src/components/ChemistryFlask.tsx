import { useMemo } from 'react';
import './ChemistryFlask.css';

interface ChemistryFlaskProps {
  level?: number; // 0 to 100
  color?: 'green' | 'violet' | 'coral';
  bubbling?: boolean;
  size?: number; // width/height in px
  className?: string;
}

export const ChemistryFlask = ({
  level = 60,
  color = 'green',
  bubbling = true,
  size = 120,
  className = '',
}: ChemistryFlaskProps) => {
  const liquidColor = useMemo(() => {
    switch (color) {
      case 'violet':
        return {
          fill: 'url(#flask-grad-violet)',
          glow: 'rgba(170, 102, 255, 0.4)',
          bubble: '#d8b4fe',
        };
      case 'coral':
        return {
          fill: 'url(#flask-grad-coral)',
          glow: 'rgba(255, 74, 96, 0.4)',
          bubble: '#fca5a5',
        };
      case 'green':
      default:
        return {
          fill: 'url(#flask-grad-green)',
          glow: 'rgba(13, 242, 163, 0.4)',
          bubble: '#a7f3d0',
        };
    }
  }, [color]);

  // Calculate liquid translation based on level (0 = empty, 100 = full)
  // Inside a 120px height viewBox, the liquid spans y=30 to y=110 (delta of 80px)
  // Translation moves the wave path vertically
  const liquidY = 110 - (level / 100) * 80;

  // Render static/animated bubbles
  const bubbleElements = useMemo(() => {
    if (!bubbling) return null;
    return Array.from({ length: 8 }).map((_, i) => {
      const delay = i * 0.4;
      const left = 25 + (i * 7.5) % 50; // scatter horizontally between 25% and 75%
      const scale = 0.5 + (i % 3) * 0.25;
      return (
        <span
          key={i}
          className={`flask-bubble color-${color}`}
          style={{
            left: `${left}%`,
            animationDelay: `${delay}s`,
            transform: `scale(${scale})`,
          }}
        />
      );
    });
  }, [bubbling, color]);

  return (
    <div
      className={`chemistry-flask-container ${className}`}
      style={{
        width: `${size}px`,
        height: `${size * 1.1}px`,
        '--flask-glow': liquidColor.glow,
      } as React.CSSProperties}
    >
      <svg
        viewBox="0 0 100 110"
        className="flask-svg"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Gradients */}
          <linearGradient id="flask-grad-green" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#059669" />
            <stop offset="70%" stopColor="#0df2a3" />
            <stop offset="100%" stopColor="#34d399" />
          </linearGradient>
          <linearGradient id="flask-grad-violet" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#6d28d9" />
            <stop offset="70%" stopColor="#aa66ff" />
            <stop offset="100%" stopColor="#c084fc" />
          </linearGradient>
          <linearGradient id="flask-grad-coral" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#be123c" />
            <stop offset="70%" stopColor="#ff4a60" />
            <stop offset="100%" stopColor="#f43f5e" />
          </linearGradient>

          {/* Clip path inside the flask boundary */}
          <clipPath id="flask-inner-clip">
            <path d="M 38 10 L 62 10 L 62 45 L 85 96 A 8 8 0 0 1 78 105 L 22 105 A 8 8 0 0 1 15 96 L 38 45 Z" />
          </clipPath>
        </defs>

        {/* Liquid Layer with Wave Animation */}
        <g clipPath="url(#flask-inner-clip)">
          <g transform={`translate(0, ${liquidY - 50})`}>
            {/* Animated wave */}
            <path
              className="flask-liquid-wave"
              d="M -100 50 Q -75 42, -50 50 T 0 50 T 50 50 T 100 50 T 150 50 T 200 50 L 200 130 L -100 130 Z"
              fill={liquidColor.fill}
            />
          </g>
        </g>

        {/* Flask Glass Outline */}
        <path
          className="flask-glass-outline"
          d="M 38 10 L 62 10 L 62 45 L 85 96 A 8 8 0 0 1 78 105 L 22 105 A 8 8 0 0 1 15 96 L 38 45 Z"
          stroke="rgba(255, 255, 255, 0.15)"
          strokeWidth="3.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Glass reflection */}
        <path
          d="M 23 93 L 34 50"
          stroke="rgba(255, 255, 255, 0.15)"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path
          d="M 39 18 L 39 30"
          stroke="rgba(255, 255, 255, 0.12)"
          strokeWidth="1.5"
          strokeLinecap="round"
        />

        {/* Measurements markings */}
        <line x1="57" y1="65" x2="63" y2="65" stroke="rgba(255, 255, 255, 0.2)" strokeWidth="1.5" />
        <line x1="55" y1="75" x2="63" y2="75" stroke="rgba(255, 255, 255, 0.2)" strokeWidth="1.5" />
        <line x1="52" y1="85" x2="63" y2="85" stroke="rgba(255, 255, 255, 0.2)" strokeWidth="1.5" />
        <line x1="50" y1="95" x2="63" y2="95" stroke="rgba(255, 255, 255, 0.2)" strokeWidth="1.5" />
      </svg>

      {/* Bubble overlay using DOM absolute positions (handles realistic fading/scaling) */}
      <div className="flask-bubble-area" style={{ clipPath: 'polygon(38% 10%, 62% 10%, 62% 45%, 85% 90%, 85% 100%, 15% 100%, 15% 90%, 38% 45%)' }}>
        {bubbleElements}
      </div>
    </div>
  );
};
