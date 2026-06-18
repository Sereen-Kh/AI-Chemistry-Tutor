import { useSyncExternalStore } from 'react';
import type { CompanionChatMessage, LearningPage } from './types';

type CompanionStoreState = {
  isOpen: boolean;
  lastOpenedAt?: number;
  currentHint: string;
  currentPage: LearningPage | 'unknown';
  currentRoute: string;
  chatMessages: CompanionChatMessage[];
};

let state: CompanionStoreState = {
  isOpen: false,
  currentHint: 'ابدأ من مهمة اليوم، ثم انتقل إلى الدرس أو التدريب المناسب.',
  currentPage: 'unknown',
  currentRoute: '/',
  chatMessages: [],
};
const listeners = new Set<() => void>();

const emit = () => {
  listeners.forEach((listener) => listener());
};

const setState = (next: Partial<CompanionStoreState>) => {
  state = { ...state, ...next };
  emit();
};

export const aiCompanionStore = {
  getSnapshot: () => state,
  subscribe: (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  open: () => setState({ isOpen: true, lastOpenedAt: Date.now() }),
  close: () => setState({ isOpen: false }),
  toggle: () => setState({ isOpen: !state.isOpen, lastOpenedAt: !state.isOpen ? Date.now() : state.lastOpenedAt }),
  setCurrentHint: (next: { hint: string; page: LearningPage | 'unknown'; route: string }) => {
    if (
      state.currentHint === next.hint &&
      state.currentPage === next.page &&
      state.currentRoute === next.route
    ) {
      return;
    }
    setState({
      currentHint: next.hint,
      currentPage: next.page,
      currentRoute: next.route,
    });
  },
  addChatMessage: (message: CompanionChatMessage) => {
    if (state.chatMessages.some((item) => item.id === message.id)) return;
    setState({ chatMessages: [...state.chatMessages, message] });
  },
};

export const useAICompanionStore = () =>
  useSyncExternalStore(aiCompanionStore.subscribe, aiCompanionStore.getSnapshot, aiCompanionStore.getSnapshot);
