import { useEffect, useMemo, useRef, useState } from 'react';
import type { RefObject } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  aiApi,
  messageResponseToAskResponse,
  resolveMediaUrl,
  toErrorMessage,
} from '../api';
import {
  Button,
  Card,
  ErrorBanner,
  FormattedText,
  LoadingSkeleton,
  PageHeader,
  StatusPill,
} from '../components/DesignSystem';
import { savePreferences } from '../lib/storage';
import type {
  AiAskRequest,
  AiAskResponse,
  AnswerFormat,
  ChatMessageResponse,
  ChatSessionResponse,
  ExplanationMethod,
  LearningMode,
  PreferredResponseFormat,
  SourceCitation,
  TeachingLevel,
  UserPreferences,
} from '../types';

type AnswerScope = NonNullable<AiAskRequest['answer_scope']>;
type ChatRequestedReturnType = 'auto' | 'text' | 'audio' | 'text_audio';
type RecordingState = 'idle' | 'recording' | 'recorded' | 'uploading' | 'failed';
type AttachmentKind = 'image' | 'file';

interface AttachmentDraft {
  file: File;
  kind: AttachmentKind;
  url?: string;
}

interface ChatItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  response?: AiAskResponse;
  question?: string;
  inputType?: 'text' | 'voice' | 'audio' | 'image' | 'file' | 'mixed' | null;
  preferredResponseFormat?: PreferredResponseFormat;
  audioUrl?: string;
  audioTranscript?: string | null;
  audioDurationSeconds?: number;
  imageUrl?: string;
  fileName?: string;
  transcriptionStatus?: string | null;
  audioStatus?: string | null;
}

interface AskAiPageProps {
  preferences: UserPreferences;
  setPreferences: (preferences: UserPreferences) => void;
}

const SUPPORTED_RESPONSE_FORMATS: PreferredResponseFormat[] = ['text', 'audio', 'image'];

const responseFormatOptions: Array<{
  value: PreferredResponseFormat;
  label: string;
  icon: string;
  description: string;
  available: boolean;
}> = [
  { value: 'text', label: 'نص', icon: 'T', description: 'إجابة عربية واضحة مع المصادر.', available: true },
  { value: 'audio', label: 'صوت', icon: 'A', description: 'إجابة صوتية مع حفظ النص.', available: true },
  { value: 'image', label: 'صورة', icon: 'I', description: 'شرح بصري أو صفحة مصدر عند توفرها.', available: true },
  { value: 'short_video', label: 'فيديو قصير', icon: 'V', description: 'تحويل الشرح إلى فيديو قصير.', available: false },
  { value: 'interactive', label: 'تفاعلي', icon: 'X', description: 'تجربة تفاعلية خطوة بخطوة.', available: false },
  { value: 'quiz', label: 'اختبار', icon: 'Q', description: 'توليد اختبار من الإجابة.', available: false },
  { value: 'flashcards', label: 'بطاقات', icon: 'F', description: 'توليد بطاقات مراجعة.', available: false },
];

const teachingLevelLabels: Array<{ value: TeachingLevel; label: string }> = [
  { value: 'simple', label: 'مبسط' },
  { value: 'standard', label: 'قياسي' },
  { value: 'academic', label: 'أكاديمي' },
];

const explanationMethodLabels: Array<{ value: ExplanationMethod; label: string }> = [
  { value: 'direct', label: 'مباشر' },
  { value: 'step_by_step', label: 'خطوة بخطوة' },
  { value: 'hints_first', label: 'تلميحات أولاً' },
  { value: 'exam_mode', label: 'نمط امتحاني' },
  { value: 'real_life_example', label: 'مثال من الحياة' },
];

const answerScopeLabels: Array<{ value: AnswerScope; label: string }> = [
  { value: 'auto', label: 'تلقائي' },
  { value: 'book_only', label: 'من الكتاب فقط' },
  { value: 'tutor_general', label: 'شرح عام عند الحاجة' },
];

const suggestedChemistryQuestions = [
  'ما هو الماء؟',
  'ما هي الحموض؟',
  'لماذا نضيف الحمض إلى الماء وليس العكس؟',
  'ما هو التركيز المولي؟',
  'محلول HCl حجمه 100 mL ويحتوي 3.65 g. احسب التركيز الغرامي والمولي؟',
];

const preferenceLabel = (value: string): string =>
  ({
    simple: 'مبسط',
    standard: 'قياسي',
    academic: 'أكاديمي',
    direct: 'مباشر',
    step_by_step: 'خطوة بخطوة',
    hints_first: 'تلميحات أولاً',
    exam_mode: 'نمط امتحاني',
    real_life_example: 'مثال من الحياة',
    text: 'نص',
    audio: 'صوت',
    image: 'صورة',
    short_video: 'فيديو قصير',
    interactive: 'تفاعلي',
    quiz: 'اختبار',
    flashcards: 'بطاقات',
    auto: 'تلقائي',
    book_only: 'من الكتاب فقط',
    tutor_general: 'شرح عام عند الحاجة',
  })[value] ?? value;

const parsePositiveInt = (value: string | null): number | null => {
  if (!value) return null;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
};

const legacyTeachingStyle = (level: TeachingLevel, method: ExplanationMethod): UserPreferences['teachingStyle'] => {
  if (method === 'real_life_example') return 'real_life';
  if (method === 'exam_mode' || level === 'academic') return 'exam';
  if (level === 'simple') return 'simple';
  return 'real_life';
};

const responseFormatToLearningMode = (format: PreferredResponseFormat): LearningMode => {
  if (format === 'image' || format === 'audio') return format;
  return 'text';
};

const responseFormatToAnswerFormat = (format: PreferredResponseFormat): AnswerFormat => {
  if (format === 'audio') return 'audio';
  if (format === 'image') return 'image';
  return 'text';
};

const responseFormatToRequestedReturnType = (format: PreferredResponseFormat): ChatRequestedReturnType => (
  format === 'audio' ? 'audio' : 'text'
);

const isSupportedResponseFormat = (format: PreferredResponseFormat): boolean =>
  SUPPORTED_RESPONSE_FORMATS.includes(format);

const isAnswerFormat = (value: string): value is AnswerFormat => (
  value === 'text' || value === 'audio' || value === 'image' || value === 'video'
);

const sessionTitleFromQuestion = (text: string): string => {
  const cleaned = text.trim().replace(/\s+/g, ' ');
  return cleaned ? cleaned.slice(0, 40) : 'محادثة جديدة';
};

const formatDuration = (seconds: number): string => {
  const safeSeconds = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const rest = String(safeSeconds % 60).padStart(2, '0');
  return `${minutes}:${rest}`;
};

const formatSessionTimestamp = (value: string): string => {
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return '';
  const diffMinutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000));
  if (diffMinutes < 1) return 'الآن';
  if (diffMinutes < 60) return `منذ ${diffMinutes} د`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `منذ ${diffHours} س`;
  const diffDays = Math.round(diffHours / 24);
  return `منذ ${diffDays} يوم`;
};

const mapAskAiError = (error: unknown, fallback: string): string => {
  const raw = toErrorMessage(error, fallback);
  const normalized = raw.toLowerCase();
  if (normalized.includes('field required') || normalized.includes('field_required')) return 'السؤال مطلوب';
  if (normalized.includes('not found') || normalized.includes('404')) return 'لم يتم العثور على نتيجة';
  if (normalized.includes('server') || normalized.includes('500')) return 'حدث خطأ أثناء توليد الإجابة';
  return raw || fallback;
};

const sessionMessageToChatItem = (message: ChatMessageResponse, question?: string): ChatItem => {
  const format = isAnswerFormat(message.format) ? message.format : 'text';
  const response = message.role === 'assistant'
    ? messageResponseToAskResponse(message, format)
    : undefined;
  return {
    id: String(message.id),
    role: message.role,
    content: message.content,
    response,
    question,
    inputType: message.input_type,
    audioUrl: resolveMediaUrl(message.audio_input_url || undefined),
    audioTranscript: message.audio_transcript,
    transcriptionStatus: message.transcription_status,
    audioStatus: message.audio_status,
  };
};

const sessionMessagesToChatItems = (messages: ChatMessageResponse[]): ChatItem[] => {
  let latestUserQuestion = '';
  return messages.map((message) => {
    if (message.role === 'user') {
      latestUserQuestion = message.content;
      return sessionMessageToChatItem(message);
    }
    return sessionMessageToChatItem(message, latestUserQuestion);
  });
};

const sourceConfidence = (sources: SourceCitation[], confidence?: number) => {
  const bestScore = Math.max(...sources.map((source) => source.score ?? 0), confidence ?? 0);
  if (!sources.length) return { label: 'لم أجد مصدراً كافياً في الكتاب', tone: 'gold' };
  if (bestScore >= 0.72) return { label: 'مصادر قوية', tone: 'teal' };
  return { label: 'مصادر محدودة', tone: 'gold' };
};

const AskAIHeader = ({
  compactLabel,
  onToggleHistory,
  onNewChat,
}: {
  compactLabel: string;
  onToggleHistory: () => void;
  onNewChat: () => void;
}) => (
  <PageHeader
    eyebrow="اسأل الذكاء"
    title="معلّم الكيمياء RAG"
    subtitle={`محادثات محفوظة بذاكرة جلسة. ${compactLabel}`}
    action={(
      <div className="chat-header-actions">
        <Button variant="secondary" onClick={onToggleHistory}>سجل المحادثات</Button>
        <Button onClick={onNewChat}>محادثة جديدة</Button>
      </div>
    )}
  />
);

const AnswerFormatPicker = ({
  value,
  onChange,
}: {
  value: PreferredResponseFormat;
  onChange: (format: PreferredResponseFormat) => void;
}) => (
  <div className="answer-format-picker" role="radiogroup" aria-label="اختيار صيغة إجابة الذكاء">
    {responseFormatOptions.map((option) => (
      <button
        key={option.value}
        type="button"
        role="radio"
        aria-label={`صيغة الإجابة: ${option.label}${option.available ? '' : '، قريباً'}`}
        aria-checked={value === option.value}
        disabled={!option.available}
        className={[
          'answer-format-card',
          value === option.value ? 'active' : '',
          option.available ? '' : 'coming-soon',
        ].filter(Boolean).join(' ')}
        onClick={() => {
          if (option.available) onChange(option.value);
        }}
      >
        <span className="answer-format-icon">{option.icon}</span>
        <strong>{option.label}</strong>
        <small>{option.description}</small>
        {!option.available && <em>قريباً</em>}
      </button>
    ))}
  </div>
);

const AnswerSettingsPopover = ({
  open,
  selectedResponseFormat,
  teachingLevel,
  explanationMethod,
  answerScope,
  onFormatChange,
  onTeachingLevelChange,
  onExplanationMethodChange,
  onAnswerScopeChange,
}: {
  open: boolean;
  selectedResponseFormat: PreferredResponseFormat;
  teachingLevel: TeachingLevel;
  explanationMethod: ExplanationMethod;
  answerScope: AnswerScope;
  onFormatChange: (format: PreferredResponseFormat) => void;
  onTeachingLevelChange: (level: TeachingLevel) => void;
  onExplanationMethodChange: (method: ExplanationMethod) => void;
  onAnswerScopeChange: (scope: AnswerScope) => void;
}) => {
  if (!open) return null;

  return (
    <div className="answer-settings-popover">
      <AnswerFormatPicker value={selectedResponseFormat} onChange={onFormatChange} />
      <div className="chat-toolbar answer-settings-controls">
        <label>
          مستوى الشرح
          <select value={teachingLevel} onChange={(event) => onTeachingLevelChange(event.target.value as TeachingLevel)}>
            {teachingLevelLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label>
          طريقة الشرح
          <select value={explanationMethod} onChange={(event) => onExplanationMethodChange(event.target.value as ExplanationMethod)}>
            {explanationMethodLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label>
          نطاق الإجابة
          <select value={answerScope} onChange={(event) => onAnswerScopeChange(event.target.value as AnswerScope)}>
            {answerScopeLabels.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
      </div>
    </div>
  );
};

const RagSourcePanel = ({ response }: { response: AiAskResponse }) => {
  const quality = sourceConfidence(response.sources, response.confidence);

  return (
    <div className="rag-source-panel">
      <div className="rag-source-head">
        <div>
          <strong>المصادر من الكتاب</strong>
          <span>{response.sources.length ? `${response.sources.length} مصدر يدعم الإجابة` : 'لا توجد مصادر كافية'}</span>
        </div>
        <StatusPill tone={quality.tone}>{quality.label}</StatusPill>
      </div>
      {response.sources.length > 0 && (
        <div className="rag-source-grid">
          {response.sources.map((source) => (
            <article key={`${source.chunk_id}-${source.page}`} className="rag-source-card">
              <strong>{source.title.includes('الحلول') ? 'كتاب الحلول' : 'كتاب الكيمياء'}</strong>
              <span>{source.page ? `صفحة ${source.page}` : 'صفحة غير محددة'}</span>
              {source.quote && <small>{source.quote}</small>}
              {typeof source.score === 'number' && <em>{Math.round(source.score * 100)}%</em>}
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

const ResponseActionChips = ({
  message,
  loading,
  onAskAction,
}: {
  message: ChatItem;
  loading: boolean;
  onAskAction: (question: string, action?: AiAskRequest['action']) => void;
}) => {
  if (!message.response) return null;
  const encodedQuestion = encodeURIComponent(message.question || message.content);

  return (
    <div className="answer-action-row response-action-chips">
      <button type="button" disabled>استمع <small>قريباً</small></button>
      <button type="button" disabled>حوّل إلى صورة <small>قريباً</small></button>
      <button type="button" disabled>فيديو قصير <small>قريباً</small></button>
      <Link to="/quiz" aria-label={`اختبرني عن ${message.question || 'الإجابة'}`}>اختبرني</Link>
      <button type="button" disabled>اصنع بطاقات <small>قريباً</small></button>
      <button
        type="button"
        onClick={() => onAskAction('اشرح الإجابة السابقة بطريقة أبسط وبمثال قصير.', 'simplify_previous')}
        disabled={loading}
      >
        بسّط الشرح
      </button>
      <Link to={`/guided-lab?problem=${encodedQuestion}`}>اشرح خطوة بخطوة</Link>
    </div>
  );
};

const ChatMessageBubble = ({
  message,
  loading,
  onAskAction,
}: {
  message: ChatItem;
  loading: boolean;
  onAskAction: (question: string, action?: AiAskRequest['action']) => void;
}) => (
  <article className={`chat-bubble ${message.role}`}>
    {message.role === 'assistant' && message.response && (
      <div className="answer-evidence-bar">
        <StatusPill tone={message.response.sources.length ? 'teal' : 'gold'}>
          {message.response.sources.length ? sourceConfidence(message.response.sources, message.response.confidence).label : 'لم أجد مصدراً كافياً في الكتاب'}
        </StatusPill>
        <span>
          {typeof message.response.confidence === 'number'
            ? `ثقة المصدر ${Math.round(message.response.confidence * 100)}%`
            : 'ثقة المصدر غير متاحة'}
        </span>
      </div>
    )}

    {message.role === 'user' && (message.inputType === 'audio' || message.inputType === 'voice') && message.audioUrl && (
      <div className="chat-audio-player">
        <audio controls src={message.audioUrl} />
      </div>
    )}
    {message.role === 'user' && message.imageUrl && (
      <figure className="chat-user-attachment">
        <img src={message.imageUrl} alt="مرفق من الطالب" />
      </figure>
    )}
    {message.role === 'user' && message.fileName && !message.imageUrl && (
      <div className="chat-file-chip">
        <span>ملف</span>
        <strong>{message.fileName}</strong>
      </div>
    )}

    <p>
      <FormattedText text={(message.inputType === 'audio' || message.inputType === 'voice') && message.role === 'user' ? 'رسالة صوتية' : message.content} />
    </p>

    {(message.inputType === 'audio' || message.inputType === 'voice') && message.role === 'user' && (
      <div className="chat-transcript">
        {message.transcriptionStatus === 'processing' && <StatusPill tone="gold">جاري تفريغ الصوت...</StatusPill>}
        {message.transcriptionStatus === 'failed' && <StatusPill tone="coral">تعذر فهم التسجيل. أعد المحاولة أو اكتب السؤال.</StatusPill>}
        {message.audioTranscript && (
          <small><strong>النص المفرغ:</strong> {message.audioTranscript}</small>
        )}
      </div>
    )}

    {message.response?.format === 'audio' && !message.response.audio_url && <StatusPill tone="gold">توليد الصوت قيد المعالجة.</StatusPill>}
    {message.response?.audio_url && <audio controls src={message.response.audio_url} />}
    {message.role === 'assistant' && message.audioStatus === 'failed' && <StatusPill tone="gold">تعذر توليد الصوت. الإجابة النصية متاحة.</StatusPill>}

    {message.response?.source_page_image_url && (
      <figure className="answer-media">
        <img src={message.response.source_page_image_url} alt="صفحة المصدر من كتاب الكيمياء" />
        <figcaption>صفحة المصدر من الكتاب</figcaption>
      </figure>
    )}
    {message.response?.image_url && (
      <figure className="answer-media">
        <img src={message.response.image_url} alt="صورة شرح مولدة بالذكاء الاصطناعي" />
        <figcaption>صورة شرح مولدة</figcaption>
      </figure>
    )}

    {message.role === 'assistant' && message.response && <RagSourcePanel response={message.response} />}
    {message.role === 'assistant' && (
      <ResponseActionChips message={message} loading={loading} onAskAction={onAskAction} />
    )}
  </article>
);

const SuggestedQuestions = ({
  loading,
  onAsk,
}: {
  loading: boolean;
  onAsk: (question: string) => void;
}) => (
  <div className="suggestion-row chat-suggestions" aria-label="أسئلة مقترحة">
    {suggestedChemistryQuestions.map((item) => (
      <button key={item} type="button" onClick={() => onAsk(item)} disabled={loading}>
        {item}
      </button>
    ))}
  </div>
);

const AttachmentPreview = ({
  attachment,
  onClear,
}: {
  attachment: AttachmentDraft | null;
  onClear: () => void;
}) => {
  if (!attachment) return null;

  return (
    <div className="composer-attachment-preview">
      {attachment.kind === 'image' && attachment.url ? (
        <img src={attachment.url} alt="معاينة الصورة المرفقة" />
      ) : (
        <span className="composer-file-icon">ملف</span>
      )}
      <span>{attachment.file.name}</span>
      <button type="button" onClick={onClear} aria-label="إزالة المرفق">×</button>
    </div>
  );
};

const VoiceRecorder = ({
  recordingState,
  recordingSeconds,
  recordedDurationSeconds,
  recordedAudioUrl,
  loading,
  onCancel,
  onStop,
  onSend,
}: {
  recordingState: RecordingState;
  recordingSeconds: number;
  recordedDurationSeconds: number;
  recordedAudioUrl: string;
  loading: boolean;
  onCancel: () => void;
  onStop: () => void;
  onSend: () => void;
}) => {
  if (recordingState === 'recording') {
    return (
      <div className="composer-recording-state" role="status" aria-live="polite">
        <div className="recording-meter" aria-hidden="true">
          <span /><span /><span /><span /><span />
        </div>
        <strong>جاري التسجيل {formatDuration(recordingSeconds)}</strong>
        <div className="composer-recording-actions">
          <Button variant="ghost" type="button" onClick={onCancel}>إلغاء</Button>
          <Button variant="secondary" type="button" onClick={onStop}>إيقاف</Button>
        </div>
      </div>
    );
  }

  if (recordingState !== 'recorded' && recordingState !== 'uploading') return null;

  return (
    <div className="composer-recorded-state">
      <div className="composer-audio-preview">
        <span>رسالة صوتية · {formatDuration(recordedDurationSeconds)}</span>
        <StatusPill tone={recordingState === 'uploading' ? 'gold' : 'teal'}>
          {recordingState === 'uploading' ? 'جاري تفريغ الصوت...' : 'جاهز للتفريغ عند الإرسال'}
        </StatusPill>
        {recordedAudioUrl && <audio controls src={recordedAudioUrl} />}
        <small>سيظهر النص المفرغ بعد الإرسال. يمكنك حذف التسجيل قبل إرساله.</small>
      </div>
      <div className="composer-recording-actions">
        <Button variant="ghost" type="button" onClick={onCancel} disabled={loading}>إلغاء</Button>
        <Button type="button" onClick={onSend} disabled={loading}>
          {recordingState === 'uploading' ? 'جاري الإرسال...' : 'إرسال'}
        </Button>
      </div>
    </div>
  );
};

const ChatComposer = ({
  question,
  selectedResponseFormat,
  attachment,
  attachmentMenuOpen,
  recordingState,
  recordingSeconds,
  recordedDurationSeconds,
  recordedAudioUrl,
  loading,
  inlineError,
  imageInputRef,
  fileInputRef,
  onQuestionChange,
  onSubmit,
  onStartRecording,
  onStopRecording,
  onCancelRecording,
  onSendAudio,
  onToggleAttachmentMenu,
  onSelectAttachment,
  onClearAttachment,
  onEscape,
}: {
  question: string;
  selectedResponseFormat: PreferredResponseFormat;
  attachment: AttachmentDraft | null;
  attachmentMenuOpen: boolean;
  recordingState: RecordingState;
  recordingSeconds: number;
  recordedDurationSeconds: number;
  recordedAudioUrl: string;
  loading: boolean;
  inlineError: string;
  imageInputRef: RefObject<HTMLInputElement | null>;
  fileInputRef: RefObject<HTMLInputElement | null>;
  onQuestionChange: (question: string) => void;
  onSubmit: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onCancelRecording: () => void;
  onSendAudio: () => void;
  onToggleAttachmentMenu: () => void;
  onSelectAttachment: (file: File | undefined, kind: AttachmentKind) => void;
  onClearAttachment: () => void;
  onEscape: () => void;
}) => (
  <form
    className="chat-composer"
    onSubmit={(event) => {
      event.preventDefault();
      onSubmit();
    }}
    onKeyDown={(event) => {
      if (event.key === 'Escape') onEscape();
    }}
  >
    <input
      ref={imageInputRef}
      className="sr-only"
      type="file"
      accept="image/*"
      onChange={(event) => onSelectAttachment(event.target.files?.[0], 'image')}
    />
    <input
      ref={fileInputRef}
      className="sr-only"
      type="file"
      onChange={(event) => onSelectAttachment(event.target.files?.[0], 'file')}
    />

    <div className="composer-meta-row">
      <span className="composer-response-pill">الإجابة كـ: {preferenceLabel(selectedResponseFormat)}</span>
      <AttachmentPreview attachment={attachment} onClear={onClearAttachment} />
    </div>

    <VoiceRecorder
      recordingState={recordingState}
      recordingSeconds={recordingSeconds}
      recordedDurationSeconds={recordedDurationSeconds}
      recordedAudioUrl={recordedAudioUrl}
      loading={loading}
      onCancel={onCancelRecording}
      onStop={onStopRecording}
      onSend={onSendAudio}
    />

    {(recordingState === 'idle' || recordingState === 'failed') && (
      <div className="composer-input-row">
        <Button type="submit" disabled={loading}>
          {loading ? '...' : 'إرسال'}
        </Button>
        <button
          type="button"
          className="composer-icon-button mic"
          onClick={onStartRecording}
          disabled={loading}
          aria-label="تسجيل رسالة صوتية"
        >
          🎙
        </button>
        <textarea
          value={question}
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              onSubmit();
            }
          }}
          placeholder="اكتب سؤالك هنا..."
          aria-label="سؤال للذكاء الاصطناعي"
          rows={1}
        />
        <div className="attachment-control">
          <button
            type="button"
            className="composer-icon-button"
            aria-label="إرفاق ملف أو صورة"
            aria-expanded={attachmentMenuOpen}
            onClick={onToggleAttachmentMenu}
            disabled={loading}
          >
            +
          </button>
          {attachmentMenuOpen && (
            <div className="attachment-menu" role="menu">
              <button type="button" role="menuitem" onClick={() => imageInputRef.current?.click()}>إرفاق صورة</button>
              <button type="button" role="menuitem" onClick={() => fileInputRef.current?.click()}>إرفاق ملف</button>
            </div>
          )}
        </div>
      </div>
    )}

    {inlineError && <p className="composer-inline-error" role="alert">{inlineError}</p>}
  </form>
);

export const AskAiPage = ({ preferences, setPreferences }: AskAiPageProps) => {
  const location = useLocation();
  const initialQuestion = useMemo(() => new URLSearchParams(location.search).get('question') || '', [location.search]);
  const routeLessonId = useMemo(() => {
    const params = new URLSearchParams(location.search);
    return parsePositiveInt(params.get('lessonId')) ?? parsePositiveInt(params.get('lesson_id'));
  }, [location.search]);
  const [question, setQuestion] = useState(initialQuestion);
  const [teachingLevel, setTeachingLevel] = useState<TeachingLevel>(preferences.teachingLevel);
  const [explanationMethod, setExplanationMethod] = useState<ExplanationMethod>(preferences.explanationMethod);
  const [answerScope, setAnswerScope] = useState<AnswerScope>('auto');
  const [selectedResponseFormat, setSelectedResponseFormat] = useState<PreferredResponseFormat>(
    preferences.answerFormat === 'audio' || preferences.answerFormat === 'image' ? preferences.answerFormat : 'text',
  );
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [sessionLoading, setSessionLoading] = useState(true);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const messageIdRef = useRef(0);
  const [messages, setMessages] = useState<ChatItem[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'اسألني من كتاب الكيمياء للصف التاسع. سأعرض المصادر والصفحات عندما يجدها نظام RAG.',
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [pageError, setPageError] = useState('');
  const [inlineError, setInlineError] = useState('');
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [recordedAudio, setRecordedAudio] = useState<Blob | null>(null);
  const [recordedAudioUrl, setRecordedAudioUrl] = useState('');
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [recordedDurationSeconds, setRecordedDurationSeconds] = useState(0);
  const [attachmentMenuOpen, setAttachmentMenuOpen] = useState(false);
  const [attachment, setAttachment] = useState<AttachmentDraft | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingStartedAtRef = useRef<number | null>(null);
  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const welcomeMessages = (): ChatItem[] => [
    {
      id: 'welcome',
      role: 'assistant',
      content: 'اسألني من كتاب الكيمياء للصف التاسع. سأعرض المصادر والصفحات عندما يجدها نظام RAG.',
    },
  ];

  useEffect(() => {
    setQuestion(initialQuestion);
  }, [initialQuestion]);

  useEffect(() => () => {
    if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);
  }, [recordedAudioUrl]);

  useEffect(() => () => {
    if (attachment?.url) URL.revokeObjectURL(attachment.url);
  }, [attachment?.url]);

  useEffect(() => () => {
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => {
    if (recordingState !== 'recording') return undefined;
    const intervalId = window.setInterval(() => {
      const startedAt = recordingStartedAtRef.current ?? Date.now();
      setRecordingSeconds(Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    }, 250);
    return () => window.clearInterval(intervalId);
  }, [recordingState]);

  const clearRecording = () => {
    if (recordedAudioUrl) URL.revokeObjectURL(recordedAudioUrl);
    setRecordedAudio(null);
    setRecordedAudioUrl('');
    setRecordingState('idle');
    setRecordingSeconds(0);
    setRecordedDurationSeconds(0);
    recordingStartedAtRef.current = null;
    audioChunksRef.current = [];
  };

  const clearAttachment = () => {
    if (attachment?.url) URL.revokeObjectURL(attachment.url);
    setAttachment(null);
    setAttachmentMenuOpen(false);
    if (imageInputRef.current) imageInputRef.current.value = '';
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const selectAttachment = (file: File | undefined, kind: AttachmentKind) => {
    if (!file) return;
    clearAttachment();
    setAttachment({
      file,
      kind,
      url: kind === 'image' ? URL.createObjectURL(file) : undefined,
    });
    setInlineError('');
  };

  const setSafeResponseFormat = (format: PreferredResponseFormat) => {
    if (!isSupportedResponseFormat(format)) {
      setInlineError('هذا النمط غير متاح حالياً.');
      return;
    }
    setSelectedResponseFormat(format);
    setInlineError('');
  };

  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setInlineError('المتصفح لا يدعم تسجيل الصوت. جرّب متصفحاً أحدث أو اكتب السؤال نصاً.');
      setRecordingState('failed');
      return;
    }
    try {
      clearRecording();
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const preferredType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
      const recorder = new MediaRecorder(stream, preferredType ? { mimeType: preferredType } : undefined);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];
      recordingStartedAtRef.current = Date.now();
      setRecordingSeconds(0);
      setRecordedDurationSeconds(0);
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const type = recorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunksRef.current, { type });
        const url = URL.createObjectURL(blob);
        const durationSeconds = recordingStartedAtRef.current
          ? Math.max(1, Math.round((Date.now() - recordingStartedAtRef.current) / 1000))
          : 0;
        setRecordedAudio(blob);
        setRecordedAudioUrl(url);
        setRecordedDurationSeconds(durationSeconds);
        setRecordingState('recorded');
        mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        recordingStartedAtRef.current = null;
      };
      recorder.start();
      setRecordingState('recording');
      setInlineError('');
      setPageError('');
    } catch {
      setRecordingState('failed');
      setInlineError('تعذر الوصول إلى الميكروفون. تحقق من صلاحيات المتصفح ثم أعد المحاولة.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
  };

  const upsertSession = (session: ChatSessionResponse) => {
    setSessions((current) => {
      const next = [session, ...current.filter((item) => item.id !== session.id)];
      return next.sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
    });
  };

  const loadSession = async (sessionId: number) => {
    setSessionLoading(true);
    setPageError('');
    try {
      const session = await aiApi.getSession(sessionId);
      setActiveSessionId(session.id);
      upsertSession(session);
      setMessages(session.messages.length ? sessionMessagesToChatItems(session.messages) : welcomeMessages());
      setHistoryOpen(false);
    } catch (err) {
      setPageError(mapAskAiError(err, 'تعذر تحميل المحادثة. تأكد أن الخادم يعمل ثم أعد المحاولة.'));
    } finally {
      setSessionLoading(false);
    }
  };

  const loadSessions = async () => {
    setSessionLoading(true);
    setPageError('');
    try {
      const loaded = await aiApi.listSessions();
      const sorted = [...loaded].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime());
      setSessions(sorted);
      const preferredSession = routeLessonId
        ? sorted.find((session) => session.lesson_id === routeLessonId) ?? null
        : sorted[0] ?? null;
      if (preferredSession) {
        setActiveSessionId(preferredSession.id);
        setMessages(preferredSession.messages.length ? sessionMessagesToChatItems(preferredSession.messages) : welcomeMessages());
      } else {
        setActiveSessionId(null);
        setMessages(welcomeMessages());
      }
    } catch (err) {
      setPageError(mapAskAiError(err, 'تعذر تحميل سجل المحادثات. تأكد أن backend يعمل على /api/v1.'));
    } finally {
      setSessionLoading(false);
    }
  };

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadSessions();
    }, 0);
    return () => window.clearTimeout(timeoutId);
    // Reload when a lesson-scoped Ask AI route is opened.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [routeLessonId]);

  const startNewChat = async (title = 'محادثة جديدة'): Promise<ChatSessionResponse | null> => {
    setSessionLoading(true);
    setPageError('');
    try {
      const session = await aiApi.createSession({
        title,
        ...(routeLessonId ? { lesson_id: routeLessonId } : {}),
      });
      upsertSession(session);
      setActiveSessionId(session.id);
      setMessages(welcomeMessages());
      setHistoryOpen(false);
      return session;
    } catch (err) {
      setPageError(mapAskAiError(err, 'تعذر إنشاء محادثة جديدة.'));
      return null;
    } finally {
      setSessionLoading(false);
    }
  };

  const deleteSession = async (sessionId: number) => {
    const confirmed = window.confirm('هل تريد حذف هذه المحادثة؟');
    if (!confirmed) return;
    setPageError('');
    try {
      await aiApi.deleteSession(sessionId);
      const remaining = sessions.filter((item) => item.id !== sessionId);
      setSessions(remaining);
      if (activeSessionId === sessionId) {
        if (remaining[0]) {
          await loadSession(remaining[0].id);
        } else {
          setActiveSessionId(null);
          setMessages(welcomeMessages());
        }
      }
    } catch (err) {
      setPageError(mapAskAiError(err, 'تعذر حذف المحادثة.'));
    }
  };

  const sendTextOrAttachment = async (override?: string, action?: AiAskRequest['action']) => {
    const typedText = (override ?? question).trim();
    const draftAttachment = attachment;
    const hasInput = Boolean(typedText || draftAttachment);
    if (!hasInput || loading) {
      if (!loading) setInlineError('اكتب سؤالاً أو أرفق صورة قبل الإرسال.');
      return;
    }
    if (!isSupportedResponseFormat(selectedResponseFormat)) {
      setInlineError('هذا النمط غير متاح حالياً.');
      return;
    }

    const requestText = typedText || (draftAttachment?.kind === 'image' ? 'اشرح هذه الصورة في سياق الكيمياء.' : 'اشرح هذا الملف في سياق الكيمياء.');
    const displayText = typedText || (draftAttachment?.kind === 'image' ? 'صورة مرفقة' : 'ملف مرفق');
    setQuestion('');
    setInlineError('');
    setPageError('');
    setLoading(true);
    messageIdRef.current += 1;
    const optimisticUserId = `user-${messageIdRef.current}`;
    const attachmentInputType: ChatItem['inputType'] = draftAttachment
      ? draftAttachment.kind === 'image' && typedText ? 'mixed' : draftAttachment.kind
      : 'text';
    const optimisticUserMessage: ChatItem = {
      id: optimisticUserId,
      role: 'user',
      content: displayText,
      inputType: attachmentInputType,
      imageUrl: draftAttachment?.kind === 'image' ? draftAttachment.url : undefined,
      fileName: draftAttachment?.kind === 'file' ? draftAttachment.file.name : undefined,
    };
    setMessages((current) => [...current, optimisticUserMessage]);

    try {
      let sessionId = activeSessionId;
      if (!sessionId) {
        const created = await startNewChat(sessionTitleFromQuestion(requestText));
        if (!created) return;
        sessionId = created.id;
        setMessages((current) => [...current.filter((item) => item.id !== 'welcome'), optimisticUserMessage]);
      }
      const answerFormat = responseFormatToAnswerFormat(selectedResponseFormat);
      const assistantMessage = await aiApi.sendSessionMessage(sessionId, {
        content: requestText,
        image: draftAttachment?.kind === 'image' ? draftAttachment.file : undefined,
        file: draftAttachment?.kind === 'file' ? draftAttachment.file : undefined,
        format: answerFormat,
        preferredResponseFormat: selectedResponseFormat,
        requestedReturnType: responseFormatToRequestedReturnType(selectedResponseFormat),
        answer_scope: answerScope,
        teaching_style: legacyTeachingStyle(teachingLevel, explanationMethod),
        teaching_level: teachingLevel,
        explanation_method: explanationMethod,
        learning_modes: [responseFormatToLearningMode(selectedResponseFormat)],
        student_interests: preferences.studentInterests,
        action,
      });
      const response = messageResponseToAskResponse(assistantMessage, answerFormat);
      setMessages((current) => [
        ...current,
        {
          id: String(assistantMessage.id),
          role: 'assistant',
          content: response.answer,
          response,
          question: requestText,
          preferredResponseFormat: selectedResponseFormat,
        },
      ]);
      const refreshed = await aiApi.getSession(sessionId);
      upsertSession(refreshed);
      setMessages(refreshed.messages.length ? sessionMessagesToChatItems(refreshed.messages) : welcomeMessages());
      if (draftAttachment) clearAttachment();
    } catch (err) {
      setInlineError(mapAskAiError(err, 'حدث خطأ أثناء توليد الإجابة'));
    } finally {
      setLoading(false);
    }
  };

  const sendAudio = async () => {
    if (!recordedAudio || loading) {
      if (!loading) setInlineError('سجّل رسالة صوتية قبل الإرسال.');
      return;
    }
    if (!isSupportedResponseFormat(selectedResponseFormat)) {
      setInlineError('هذا النمط غير متاح حالياً.');
      return;
    }

    setInlineError('');
    setPageError('');
    setLoading(true);
    setRecordingState('uploading');
    messageIdRef.current += 1;
    const optimisticUserId = `user-audio-${messageIdRef.current}`;
    const optimisticUserMessage: ChatItem = {
      id: optimisticUserId,
      role: 'user',
      content: 'رسالة صوتية',
      inputType: 'voice',
      audioUrl: recordedAudioUrl,
      audioDurationSeconds: recordedDurationSeconds,
      transcriptionStatus: 'processing',
    };
    setMessages((current) => [...current, optimisticUserMessage]);

    try {
      let sessionId = activeSessionId;
      if (!sessionId) {
        const created = await startNewChat('رسالة صوتية');
        if (!created) return;
        sessionId = created.id;
        setMessages((current) => [...current.filter((item) => item.id !== 'welcome'), optimisticUserMessage]);
      }
      const answerFormat = responseFormatToAnswerFormat(selectedResponseFormat);
      const assistantMessage = await aiApi.sendSessionMessage(sessionId, {
        audio: recordedAudio,
        audioFilename: 'student-message.webm',
        preferredResponseFormat: selectedResponseFormat,
        requestedReturnType: responseFormatToRequestedReturnType(selectedResponseFormat),
        language: 'ar',
        format: answerFormat,
        answer_scope: answerScope,
        teaching_style: legacyTeachingStyle(teachingLevel, explanationMethod),
        teaching_level: teachingLevel,
        explanation_method: explanationMethod,
        learning_modes: [responseFormatToLearningMode(selectedResponseFormat)],
        student_interests: preferences.studentInterests,
      });
      const response = messageResponseToAskResponse(assistantMessage, answerFormat);
      setMessages((current) => [
        ...current,
        {
          id: String(assistantMessage.id),
          role: 'assistant',
          content: response.answer,
          response,
          question: assistantMessage.audio_transcript || 'رسالة صوتية',
          inputType: assistantMessage.input_type,
          audioTranscript: assistantMessage.audio_transcript,
          audioStatus: assistantMessage.audio_status,
          preferredResponseFormat: selectedResponseFormat,
        },
      ]);
      const refreshed = await aiApi.getSession(sessionId);
      upsertSession(refreshed);
      setMessages(refreshed.messages.length ? sessionMessagesToChatItems(refreshed.messages) : welcomeMessages());
      clearRecording();
    } catch (err) {
      setRecordingState('recorded');
      setInlineError(mapAskAiError(err, 'تعذر إرسال التسجيل الصوتي. أعد التسجيل أو اكتب السؤال نصاً.'));
    } finally {
      setLoading(false);
    }
  };

  const saveTeachingLevel = (nextLevel: TeachingLevel) => {
    setTeachingLevel(nextLevel);
    const next = {
      ...preferences,
      teachingLevel: nextLevel,
      teachingStyle: legacyTeachingStyle(nextLevel, explanationMethod),
    };
    setPreferences(next);
    savePreferences(next);
  };

  const saveExplanationMethod = (nextMethod: ExplanationMethod) => {
    setExplanationMethod(nextMethod);
    const next = {
      ...preferences,
      explanationMethod: nextMethod,
      teachingStyle: legacyTeachingStyle(teachingLevel, nextMethod),
    };
    setPreferences(next);
    savePreferences(next);
  };

  const compactPreferenceLabel = [
    preferenceLabel(teachingLevel),
    preferenceLabel(explanationMethod),
    `الإجابة كـ: ${preferenceLabel(selectedResponseFormat)}`,
  ].join(' · ');
  const activeSession = sessions.find((session) => session.id === activeSessionId);
  const activeLessonContext = routeLessonId ? `درس محدد #${routeLessonId}` : 'كل الكتاب';

  return (
    <div className="ask-layout">
      <AskAIHeader
        compactLabel={compactPreferenceLabel}
        onToggleHistory={() => setHistoryOpen((open) => !open)}
        onNewChat={() => void startNewChat()}
      />

      <div className={historyOpen ? 'chat-session-workspace history-open' : 'chat-session-workspace'}>
        <aside className="chat-history-sidebar" aria-label="سجل محادثات الذكاء">
          <div className="chat-history-head">
            <div>
              <strong>المحادثات</strong>
              <span>{sessions.length ? `${sessions.length} جلسة محفوظة` : 'لا توجد جلسات بعد'}</span>
            </div>
            <Button variant="ghost" onClick={() => void loadSessions()} disabled={sessionLoading}>تحديث</Button>
          </div>
          {sessionLoading && !sessions.length ? (
            <LoadingSkeleton rows={4} />
          ) : sessions.length ? (
            <div className="chat-session-list">
              {sessions.map((session) => {
                const lastMessage = [...(session.messages || [])].reverse().find((item) => item.content);
                return (
                  <button
                    type="button"
                    key={session.id}
                    className={session.id === activeSessionId ? 'chat-session-item active' : 'chat-session-item'}
                    onClick={() => void loadSession(session.id)}
                  >
                    <span>
                      <strong>{session.title || 'محادثة كيمياء'}</strong>
                      <small>{lastMessage?.content || 'ابدأ بسؤال جديد'}</small>
                    </span>
                    <em>{formatSessionTimestamp(session.updated_at)}</em>
                    <span
                      role="button"
                      tabIndex={0}
                      className="chat-session-delete"
                      aria-label={`حذف ${session.title || 'المحادثة'}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        void deleteSession(session.id);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          event.stopPropagation();
                          void deleteSession(session.id);
                        }
                      }}
                    >
                      حذف
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="chat-session-empty">
              <strong>ابدأ أول محادثة</strong>
              <p>سيتم حفظ الأسئلة والإجابات هنا لتستطيع الرجوع إليها لاحقاً.</p>
            </div>
          )}
        </aside>

        <Card className="chat-panel">
          <div className="active-session-strip">
            <span>الجلسة الحالية</span>
            <strong>{activeSession?.title || 'محادثة جديدة'}</strong>
            <small>{activeLessonContext} · {activeSession ? `آخر تحديث ${formatSessionTimestamp(activeSession.updated_at)}` : 'سيتم إنشاء جلسة عند إرسال أول سؤال'}</small>
          </div>

          <div className="chat-settings-summary ask-answer-summary">
            <button
              type="button"
              className="answer-format-compact"
              onClick={() => setSettingsOpen((open) => !open)}
              aria-expanded={settingsOpen}
            >
              الإجابة كـ: {preferenceLabel(selectedResponseFormat)} <span>▼</span>
            </button>
            <span>{preferenceLabel(answerScope)}</span>
            <Button variant="ghost" onClick={() => setSettingsOpen((open) => !open)} className="ed-btn-xs">
              {settingsOpen ? 'إخفاء الإعدادات' : 'إعدادات الإجابة'}
            </Button>
          </div>

          <AnswerSettingsPopover
            open={settingsOpen}
            selectedResponseFormat={selectedResponseFormat}
            teachingLevel={teachingLevel}
            explanationMethod={explanationMethod}
            answerScope={answerScope}
            onFormatChange={setSafeResponseFormat}
            onTeachingLevelChange={saveTeachingLevel}
            onExplanationMethodChange={saveExplanationMethod}
            onAnswerScopeChange={setAnswerScope}
          />

          {pageError && <ErrorBanner message={pageError} onRetry={() => void loadSessions()} />}

          <div className="chat-feed">
            {sessionLoading ? (
              <LoadingSkeleton rows={5} />
            ) : (
              messages.map((message) => (
                <ChatMessageBubble
                  key={message.id}
                  message={message}
                  loading={loading}
                  onAskAction={(text, action) => void sendTextOrAttachment(text, action)}
                />
              ))
            )}
            {loading && <div className="typing-dots" aria-label="الذكاء يكتب الإجابة" role="status"><span /><span /><span /></div>}
          </div>

          <SuggestedQuestions loading={loading} onAsk={(text) => void sendTextOrAttachment(text)} />

          <div className="chat-actions">
            <Button
              variant="secondary"
              onClick={() => void sendTextOrAttachment('اشرح هذا بطريقة أبسط مع مثال واضح.', 'rephrase_previous')}
              disabled={loading}
            >
              أعد الشرح
            </Button>
            <Button variant="ghost" onClick={() => setInlineError('تم تسجيل أنك فهمت هذه الإجابة في الجلسة الحالية.')}>فهمت</Button>
          </div>

          <ChatComposer
            question={question}
            selectedResponseFormat={selectedResponseFormat}
            attachment={attachment}
            attachmentMenuOpen={attachmentMenuOpen}
            recordingState={recordingState}
            recordingSeconds={recordingSeconds}
            recordedDurationSeconds={recordedDurationSeconds}
            recordedAudioUrl={recordedAudioUrl}
            loading={loading}
            inlineError={inlineError}
            imageInputRef={imageInputRef}
            fileInputRef={fileInputRef}
            onQuestionChange={(value) => {
              setQuestion(value);
              if (value.trim()) setInlineError('');
            }}
            onSubmit={() => void sendTextOrAttachment()}
            onStartRecording={() => void startRecording()}
            onStopRecording={stopRecording}
            onCancelRecording={clearRecording}
            onSendAudio={() => void sendAudio()}
            onToggleAttachmentMenu={() => setAttachmentMenuOpen((open) => !open)}
            onSelectAttachment={selectAttachment}
            onClearAttachment={clearAttachment}
            onEscape={() => {
              if (recordingState === 'recording' || recordingState === 'recorded') clearRecording();
              setAttachmentMenuOpen(false);
            }}
          />
        </Card>
      </div>
    </div>
  );
};
