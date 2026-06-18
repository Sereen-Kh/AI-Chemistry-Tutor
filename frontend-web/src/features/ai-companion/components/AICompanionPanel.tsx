import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { aiCompanionApi } from '../api/aiCompanionApi';
import { aiCompanionStore, useAICompanionStore } from '../aiCompanionStore';
import { buildCompanionSuggestions } from '../companionLogic';
import type { CompanionAction, LearningContext } from '../types';
import { AIContextSuggestions } from './AIContextSuggestions';

export const AICompanionPanel = ({
  context,
  onClose,
}: {
  context: LearningContext;
  onClose: () => void;
}) => {
  const navigate = useNavigate();
  const panelRef = useRef<HTMLDivElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const chatHistoryRef = useRef<HTMLDivElement | null>(null);
  const { currentHint, chatMessages } = useAICompanionStore();
  const [actions, setActions] = useState<CompanionAction[]>(() => buildCompanionSuggestions(context));
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    aiCompanionApi.getCompanionSuggestions(context).then((response) => {
      if (cancelled) return;
      setActions(response.suggestedActions);
    });
    return () => {
      cancelled = true;
    };
  }, [context]);

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>('button, a, input, textarea, [tabindex]:not([tabindex="-1"])'),
      ).filter((node) => !node.hasAttribute('disabled'));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  useEffect(() => {
    const chatHistory = chatHistoryRef.current;
    if (chatHistory) chatHistory.scrollTop = chatHistory.scrollHeight;
  }, [chatMessages.length]);

  const sendMessage = async () => {
    const value = input.trim();
    if (!value || loading) return;
    const createdAt = Date.now();
    aiCompanionStore.addChatMessage({
      id: `user-${createdAt}`,
      role: 'user',
      content: value,
      createdAt,
    });
    setInput('');
    setLoading(true);
    try {
      const response = await aiCompanionApi.sendCompanionMessage(value, context);
      aiCompanionStore.addChatMessage({
        id: `assistant-${createdAt}`,
        role: 'assistant',
        content: response.message,
        createdAt: Date.now(),
      });
      setActions(response.suggestedActions);
    } finally {
      setLoading(false);
    }
  };

  const onAction = async (action: CompanionAction) => {
    if (action.kind === 'explain_lesson') {
      const response = await aiCompanionApi.explainCurrentLesson(context);
      if (response.targetRoute) navigate(response.targetRoute);
      onClose();
      return;
    }
    if (action.kind === 'quiz') {
      const response = await aiCompanionApi.generateQuizFromContext(context);
      if (response.targetRoute) navigate(response.targetRoute);
      onClose();
      return;
    }
    if (action.kind === 'flashcards') {
      const response = await aiCompanionApi.generateFlashcardsFromContext(context);
      if (response.targetRoute) navigate(response.targetRoute);
      onClose();
      return;
    }
    if (action.targetRoute) {
      navigate(action.targetRoute);
      onClose();
    }
  };

  return (
    <div className="ai-companion-panel-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section
        ref={panelRef}
        className="ai-companion-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ai-companion-title"
      >
        <header className="ai-companion-panel-head">
          <div>
            <p className="eyebrow">مرشد EduMind</p>
            <h2 id="ai-companion-title">رفيق الكيمياء الذكي</h2>
          </div>
          <button ref={closeRef} type="button" className="ai-companion-close" onClick={onClose} aria-label="إغلاق المرشد">
            ×
          </button>
        </header>

        <div className="ai-companion-context-card">
          <span>السياق الحالي</span>
          <strong>
            {context.activeLessonTitleAr || context.activeUnitTitleAr || (
              context.currentPage === 'study_plan' ? 'خطة الدراسة' : 'منصة التعلم'
            )}
          </strong>
          <p>{currentHint}</p>
        </div>

        <AIContextSuggestions actions={actions} onAction={onAction} />

        <div ref={chatHistoryRef} className="ai-companion-chat-history" aria-label="محادثة مرشد EduMind">
          {chatMessages.length === 0 ? (
            <p className="ai-companion-empty-chat">لن أضيف رسائل عند التنقل. اكتب سؤالاً هنا لبدء محادثة مع المرشد.</p>
          ) : (
            chatMessages.map((item) => (
              <article className={`ai-companion-chat-bubble ${item.role}`} key={item.id}>
                {item.content}
              </article>
            ))
          )}
        </div>

        <div className="ai-companion-message-box">
          <label htmlFor="ai-companion-input">اسأل المرشد عن الخطوة التالية</label>
          <div>
            <input
              id="ai-companion-input"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') void sendMessage();
              }}
              placeholder="مثلاً: ماذا أدرس الآن؟"
            />
            <button type="button" onClick={sendMessage} disabled={!input.trim() || loading}>
              {loading ? '...' : 'إرسال'}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};
