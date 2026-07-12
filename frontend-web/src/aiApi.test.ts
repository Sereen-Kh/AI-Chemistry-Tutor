import { afterEach, describe, expect, it } from 'vitest';
import type { AxiosAdapter, InternalAxiosRequestConfig } from 'axios';

import { aiApi } from './api/aiApi';
import { api } from './api/http';
import type { ChatMessageResponse, ChatSessionResponse } from './types';


const now = new Date().toISOString();

const messageResponse: ChatMessageResponse = {
  id: 2,
  session_id: 10,
  role: 'assistant',
  content: 'إجابة اختبارية',
  format: 'text',
  created_at: now,
};

const sessionResponse: ChatSessionResponse = {
  id: 10,
  user_id: 1,
  lesson_id: null,
  title: 'جلسة اختبار',
  style: null,
  created_at: now,
  updated_at: now,
  messages: [],
};

const originalAdapter = api.defaults.adapter;

afterEach(() => {
  api.defaults.adapter = originalAdapter;
});

describe('aiApi transport content types', () => {
  it('keeps audio chat as FormData so the browser can add the multipart boundary', async () => {
    const captured: InternalAxiosRequestConfig[] = [];
    const adapter: AxiosAdapter = async (config) => {
      captured.push(config);
      return {
        data: messageResponse,
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      };
    };
    api.defaults.adapter = adapter;

    await aiApi.sendVoiceMessage(
      10,
      new Blob(['recorded audio'], { type: 'audio/webm' }),
      {
        requestedReturnType: 'text_audio',
        language: 'ar',
      },
    );

    const request = captured[0];
    expect(request).toBeDefined();
    if (!request) throw new Error('Audio request was not captured');
    expect(request.data).toBeInstanceOf(FormData);
    const formData = request.data as FormData;
    expect(formData.get('conversationId')).toBe('10');
    expect(formData.get('requestedReturnType')).toBe('text_audio');
    expect(formData.get('language')).toBe('ar');
    expect(formData.get('audio')).toBeInstanceOf(File);
    expect(request.headers.getContentType()).not.toBe('application/json');
  });

  it('continues to serialize ordinary API objects as JSON', async () => {
    const captured: InternalAxiosRequestConfig[] = [];
    const adapter: AxiosAdapter = async (config) => {
      captured.push(config);
      return {
        data: sessionResponse,
        status: 201,
        statusText: 'Created',
        headers: {},
        config,
      };
    };
    api.defaults.adapter = adapter;

    await aiApi.createSession({ title: 'جلسة اختبار' });

    const request = captured[0];
    expect(request).toBeDefined();
    if (!request) throw new Error('JSON request was not captured');
    expect(request.data).toBe(JSON.stringify({ title: 'جلسة اختبار' }));
    expect(request.headers.getContentType()).toBe('application/json');
  });
});
