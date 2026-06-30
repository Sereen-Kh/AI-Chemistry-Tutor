import { api } from './http';

export interface HomeworkSource {
  chunk_id?: string | number;
  page_number?: number;
  page?: number;
  source_type?: string;
  content_type?: string;
  preview?: string;
  quote?: string;
  score?: number;
}

export interface HomeworkSolveTextResponse {
  id: number;
  problem_text: string;
  extracted_text?: string | null;
  solution: string;
  source_chunks?: HomeworkSource[] | Record<string, unknown> | null;
  confidence_score?: number | null;
  created_at: string;
}

export interface HomeworkUploadResponse {
  homework_id: number;
  image_url: string;
  image_path: string;
  filename: string;
  content_type?: string | null;
}

export interface HomeworkSolveImageResponse {
  id: number;
  problem_text: string;
  extracted_text?: string | null;
  solution: string;
  source_chunks?: HomeworkSource[] | Record<string, unknown> | null;
  confidence_score?: number | null;
  image_url?: string | null;
  created_at: string;
}

export const homeworkApi = {
  async solveText(problemText: string): Promise<HomeworkSolveTextResponse> {
    const { data } = await api.post<HomeworkSolveTextResponse>('/homework/solve-text', {
      problem_text: problemText,
    });
    return data;
  },

  async uploadImage(file: File, topicId?: number): Promise<HomeworkUploadResponse> {
    const form = new FormData();
    form.append('file', file);
    if (topicId !== undefined) form.append('topic_id', String(topicId));
    const { data } = await api.post<HomeworkUploadResponse>('/homework/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async solveImage(imagePath: string, topicId?: number): Promise<HomeworkSolveImageResponse> {
    const { data } = await api.post<HomeworkSolveImageResponse>('/homework/solve-image', {
      image_path: imagePath,
      ...(topicId !== undefined && { topic_id: topicId }),
    });
    return data;
  },
};

