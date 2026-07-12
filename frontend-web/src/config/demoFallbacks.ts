export const allowDemoFallbacks =
  import.meta.env.DEV && import.meta.env.VITE_ALLOW_DEMO_FALLBACKS === 'true';

export const demoFallbackDisabledMessage =
  'تعذر تحميل البيانات من الخادم. بيانات التجربة معطلة في هذا الوضع.';
