import { useCallback, useEffect, useState } from 'react';
import { studyPlanApi } from '../api';
import type { StudyPlan, StudyPlanProgress } from '../types';

export const useStudyPlanProgress = (plan: StudyPlan | null) => {
  const [progress, setProgress] = useState<StudyPlanProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!plan) {
      setProgress(null);
      return;
    }
    if (!plan.id) {
      setProgress(null);
      setError('لا توجد خطة دراسة محفوظة لتحميل التقدم.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const nextProgress = await studyPlanApi.getStudyPlanProgress(plan.id, plan);
      setProgress(nextProgress);
    } catch {
      setError('تعذر تحميل تقدّم الخطة.');
    } finally {
      setLoading(false);
    }
  }, [plan]);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  return { progress, loading, error, refetch };
};
