import { motion } from 'framer-motion';
import { useLocation } from 'react-router-dom';
import './AvatarGuide.css';

export type AvatarExpression =
  | 'idle'
  | 'happy'
  | 'thinking'
  | 'studying'
  | 'lab'
  | 'welcome'
  | 'pointing'
  | 'speaking'
  | 'celebrating'
  | 'video';

export type AvatarWaypoint =
  | 'sidebar'
  | 'inline'
  | 'top-left'
  | 'top-right'
  | 'center-left'
  | 'center-right'
  | 'bottom-left'
  | 'bottom-right';

interface AvatarGuideProps {
  expression?: AvatarExpression;
  message?: string;
  waypoint?: AvatarWaypoint;
  compact?: boolean;
}

const defaultMessages: Record<AvatarExpression, string> = {
  idle: 'أنا مرشدك في الكيمياء، جاهز عندما تبدأ.',
  happy: 'مهمة اليوم جاهزة. لنبدأ من مصدر واضح في الكتاب.',
  thinking: 'اسألني من كتاب الكيمياء وسأبحث عن الصفحات المناسبة.',
  studying: 'راجع الخطة والبطاقات، وركز على الموضوعات الضعيفة.',
  lab: 'أدخل المعادلة وسنوازنها خطوة بخطوة.',
  welcome: 'أهلاً بك في مختبر EduMind.',
  pointing: 'انتبه إلى المصادر والصفحات قبل اعتماد الإجابة.',
  speaking: 'سأشرح بالعربية مع أمثلة مناسبة للصف التاسع.',
  celebrating: 'إنجاز جيد. تابع إلى السؤال التالي.',
  video: 'صيغة Reel جاهزة في الواجهة عند طلب شرح بصري قصير.',
};

const routeGuide = (path: string): { expression: AvatarExpression; message: string; waypoint: AvatarWaypoint } => {
  if (path.includes('login') || path.includes('register')) {
    return {
      expression: 'welcome',
      message: 'أهلاً، أنا مرشدك الهجين في مختبر EduMind.',
      waypoint: 'top-left',
    };
  }
  if (path.includes('onboarding')) {
    return {
      expression: 'pointing',
      message: 'اختر اهتماماتك وطريقة الشرح التي تناسبك.',
      waypoint: 'center-left',
    };
  }
  if (path.includes('dashboard')) {
    return {
      expression: 'happy',
      message: 'مهمتك اليومية جاهزة مع مصادر من كتاب الكيمياء.',
      waypoint: 'sidebar',
    };
  }
  if (path.includes('ask-ai')) {
    return {
      expression: 'thinking',
      message: 'اسألني من الكتاب وسأعرض الصفحات والمقاطع الأقرب.',
      waypoint: 'sidebar',
    };
  }
  if (path.includes('study-plan')) {
    return {
      expression: 'studying',
      message: 'هذه خريطة دروسك ونقاط الضعف التي تحتاج مراجعة.',
      waypoint: 'sidebar',
    };
  }
  if (path.includes('flashcards')) {
    return {
      expression: 'celebrating',
      message: 'اقلب البطاقة ثم قيّم تذكرك بصدق.',
      waypoint: 'sidebar',
    };
  }
  if (path.includes('balancer')) {
    return {
      expression: 'lab',
      message: 'أدخل معادلة كيميائية وسنوازنها في المختبر.',
      waypoint: 'sidebar',
    };
  }
  if (path.includes('profile')) {
    return {
      expression: 'speaking',
      message: 'من هنا تضبط تفضيلات الشرح واللغة وصيغة الإجابة.',
      waypoint: 'sidebar',
    };
  }

  return {
    expression: 'idle',
    message: defaultMessages.idle,
    waypoint: 'sidebar',
  };
};

export const AvatarGuide = ({
  expression: customExpression,
  message: customMessage,
  waypoint: customWaypoint,
  compact = false,
}: AvatarGuideProps) => {
  const location = useLocation();
  const guide = routeGuide(location.pathname);
  const expression = customExpression || guide.expression;
  const bubbleText = customMessage || (customExpression ? defaultMessages[expression] : guide.message);
  const waypoint = customWaypoint || guide.waypoint;

  const activeColor =
    expression === 'lab'
      ? '#ff4a60'
      : expression === 'thinking' || expression === 'video'
        ? '#aa66ff'
        : '#0df2a3';

  return (
    <motion.div
      className={`avatar-guide-container expression-${expression} waypoint-${waypoint} ${compact ? 'compact' : ''}`}
      initial={{ opacity: 0, scale: 0.94, y: 12 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="avatar-bubble">
        <p>{bubbleText}</p>
        <div className="bubble-arrow" />
      </div>

      <div className="avatar-visual">
        <svg
          viewBox="0 0 100 100"
          className="avatar-svg"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Define filters for visor glow */}
          <defs>
            <filter id="avatar-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Hybrid lab mascot: robot visor, beaker body, tutor coat. */}
          <ellipse cx="50" cy="52" rx="36" ry="36" fill="rgba(22, 25, 31, 0.9)" stroke="rgba(255, 255, 255, 0.1)" strokeWidth="1.5" />

          {/* Bubbles in head */}
          {(expression === 'lab' || expression === 'thinking' || expression === 'video') && (
            <>
              <circle cx="42" cy="45" r="2.5" fill="#0df2a3" opacity="0.6" className="head-bubble" style={{ animationDelay: '0.2s' }} />
              <circle cx="58" cy="35" r="1.5" fill="#aa66ff" opacity="0.6" className="head-bubble" style={{ animationDelay: '0.8s' }} />
              <circle cx="50" cy="40" r="2" fill="#0df2a3" opacity="0.6" className="head-bubble" style={{ animationDelay: '1.4s' }} />
            </>
          )}

          {/* Robot Core Body */}
          <circle cx="50" cy="52" r="30" fill="url(#body-gradient)" stroke="#2d3442" strokeWidth="2.5" />
          <linearGradient id="body-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#1e242d" />
            <stop offset="100%" stopColor="#0d0f12" />
          </linearGradient>

          {/* Tutor lab coat lower shell */}
          <path d="M28 72 C34 86 66 86 72 72 L62 91 H38 Z" fill="rgba(241, 245, 249, 0.9)" stroke="rgba(255,255,255,0.35)" strokeWidth="1" />
          <path d="M50 75 L44 91 M50 75 L56 91" stroke="#2d3442" strokeWidth="1.4" strokeLinecap="round" />
          <circle cx="50" cy="84" r="1.5" fill="#0df2a3" />

          {/* Safety Goggles Band */}
          <rect x="18" y="44" width="64" height="15" rx="3" fill="#16191f" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="1" />

          {/* Safety Goggles / Glowing Visor */}
          <rect
            className="avatar-visor"
            x="22"
            y="42"
            width="56"
            height="18"
            rx="6"
            fill="#0f172a"
            stroke={activeColor}
            strokeWidth="2.5"
            style={{ filter: 'url(#avatar-glow)' }}
          />

          {/* Route-Based Eyes/Visor expressions */}
          {(expression === 'happy' || expression === 'celebrating' || expression === 'welcome') && (
            <g className="eye-group happy">
              <path d="M 33 52 Q 38 47, 43 52" stroke="#0df2a3" strokeWidth="3" strokeLinecap="round" />
              <path d="M 57 52 Q 62 47, 67 52" stroke="#0df2a3" strokeWidth="3" strokeLinecap="round" />
            </g>
          )}

          {(expression === 'thinking' || expression === 'pointing' || expression === 'video') && (
            <g className="eye-group thinking">
              <line x1="32" y1="49" x2="44" y2="52" stroke="#aa66ff" strokeWidth="3" strokeLinecap="round" />
              <line x1="56" y1="52" x2="68" y2="49" stroke="#aa66ff" strokeWidth="3" strokeLinecap="round" />
            </g>
          )}

          {expression === 'studying' && (
            <g className="eye-group studying">
              <ellipse cx="38" cy="51" rx="4" ry="2.5" fill="#0df2a3" />
              <ellipse cx="62" cy="51" rx="4" ry="2.5" fill="#0df2a3" />
              <line x1="32" y1="46" x2="44" y2="46" stroke="#0df2a3" strokeWidth="1.5" />
              <line x1="56" y1="46" x2="68" y2="46" stroke="#0df2a3" strokeWidth="1.5" />
            </g>
          )}

          {expression === 'lab' && (
            <g className="eye-group lab">
              <circle cx="38" cy="51" r="3.5" fill="#ff4a60" />
              <circle cx="62" cy="51" r="3.5" fill="#ff4a60" />
            </g>
          )}

          {expression === 'idle' && (
            <g className="eye-group idle">
              <line x1="34" y1="51" x2="42" y2="51" stroke="#0df2a3" strokeWidth="3" strokeLinecap="round" />
              <line x1="58" y1="51" x2="66" y2="51" stroke="#0df2a3" strokeWidth="3" strokeLinecap="round" />
            </g>
          )}

          {/* Little Cheek Rosy Lights */}
          <circle cx="28" cy="67" r="3" fill="#ff4a60" opacity="0.3" />
          <circle cx="72" cy="67" r="3" fill="#ff4a60" opacity="0.3" />

          {/* Mouth */}
          {expression === 'happy' || expression === 'celebrating' || expression === 'welcome' ? (
            <path d="M 46 68 Q 50 72, 54 68" stroke="#0df2a3" strokeWidth="2.5" strokeLinecap="round" />
          ) : expression === 'thinking' || expression === 'pointing' || expression === 'video' ? (
            <line x1="47" y1="69" x2="53" y2="69" stroke="#aa66ff" strokeWidth="2" strokeLinecap="round" />
          ) : expression === 'speaking' ? (
            <ellipse cx="50" cy="69" rx="3.4" ry="2.4" stroke="#0df2a3" strokeWidth="1.8" />
          ) : (
            <line x1="48" y1="69" x2="52" y2="69" stroke="#94a3b8" strokeWidth="1.5" strokeLinecap="round" />
          )}

          {(expression === 'pointing' || expression === 'video') && (
            <g className="pointer-arm">
              <path d="M73 67 C85 62 88 52 83 45" stroke={activeColor} strokeWidth="3" strokeLinecap="round" fill="none" />
              <path d="M82 44 L87 46 L83 49" stroke={activeColor} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
            </g>
          )}

          {/* Cute antenna */}
          <path d="M 50 22 L 50 12" stroke="#2d3442" strokeWidth="3" strokeLinecap="round" />
          <circle cx="50" cy="10" r="4.5" fill={activeColor} style={{ filter: 'url(#avatar-glow)' }} />
        </svg>
      </div>
    </motion.div>
  );
};
