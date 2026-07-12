import { AnimatePresence, motion } from 'framer-motion';
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { aiCompanionStore, useAICompanionStore } from '../aiCompanionStore';
import { buildCompanionMessage } from '../companionLogic';
import { useLearningContext } from '../useLearningContext';
import { AICompanionAvatar } from './AICompanionAvatar';
import { AICompanionPanel } from './AICompanionPanel';

export const AICompanion = () => {
  const context = useLearningContext();
  const { isOpen, currentHint } = useAICompanionStore();
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const seenTooltipRoutes = useRef<Set<string>>(new Set());
  const [dismissedTooltipRoutes, setDismissedTooltipRoutes] = useState<Set<string>>(() => new Set());
  const [tooltipRoute, setTooltipRoute] = useState<string | null>(null);
  const [isHintHovered, setIsHintHovered] = useState(false);
  const hint = useMemo(() => buildCompanionMessage(context), [context]);

  useEffect(() => {
    aiCompanionStore.setCurrentHint({
      hint,
      page: context.currentPage,
      route: context.currentRoute,
    });
    if (!seenTooltipRoutes.current.has(context.currentRoute) && !dismissedTooltipRoutes.has(context.currentRoute)) {
      seenTooltipRoutes.current.add(context.currentRoute);
      setTooltipRoute(context.currentRoute);
    }
  }, [context.currentPage, context.currentRoute, dismissedTooltipRoutes, hint]);

  useEffect(() => {
    if (!tooltipRoute || isOpen) return undefined;
    const hideTimer = window.setTimeout(() => {
      setTooltipRoute((current) => (current === tooltipRoute ? null : current));
    }, 5000);
    return () => window.clearTimeout(hideTimer);
  }, [isOpen, tooltipRoute]);

  useEffect(() => {
    if (isOpen) queueMicrotask(() => setTooltipRoute(null));
  }, [isOpen]);

  const close = () => {
    aiCompanionStore.close();
    window.setTimeout(() => buttonRef.current?.focus(), 0);
  };

  const dismissHint = () => {
    setDismissedTooltipRoutes((current) => {
      const next = new Set(current);
      next.add(context.currentRoute);
      return next;
    });
    setTooltipRoute(null);
    setIsHintHovered(false);
  };

  if (typeof document === 'undefined') return null;

  const showHintTooltip = !isOpen
    && Boolean(currentHint)
    && !dismissedTooltipRoutes.has(context.currentRoute)
    && (isHintHovered || tooltipRoute === context.currentRoute);

  return createPortal(
    <>
      <motion.div
        className="ai-companion"
        initial={{ opacity: 0, y: 18, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
      >
        <button
          ref={buttonRef}
          type="button"
          className="ai-companion-button"
          onClick={aiCompanionStore.toggle}
          onMouseEnter={() => setIsHintHovered(true)}
          onMouseLeave={() => setIsHintHovered(false)}
          onFocus={() => setIsHintHovered(true)}
          onBlur={() => setIsHintHovered(false)}
          aria-label="فتح مرشد EduMind"
          aria-expanded={isOpen}
        >
          <AICompanionAvatar context={context} />
          <span className="sr-only">فتح مرشد EduMind</span>
        </button>
        <AnimatePresence>
          {showHintTooltip && (
            <motion.div
              key={context.currentRoute}
              className="ai-companion-hint"
              initial={{ opacity: 0, y: 8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.96 }}
              transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
              role="status"
            >
              <span>{currentHint}</span>
              <button type="button" onClick={dismissHint} aria-label="إخفاء تلميح مرشد EduMind">
                ×
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            key="ai-companion-panel"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
          >
            <AICompanionPanel context={context} onClose={close} />
          </motion.div>
        )}
      </AnimatePresence>
    </>,
    document.body,
  );
};
