import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  askChemistry,
  getHealth,
  resolveMediaUrl,
  type AnswerBlock,
  type ChatAnswer,
  type PreferredAnswerType,
} from './api';

// Pages
const Dashboard = () => {
  const [health, setHealth] = useState<string>('Checking...');
  
  useEffect(() => {
    getHealth().then(res => setHealth(res.status)).catch(() => setHealth('Error'));
  }, []);

  return (
    <div className="glass-panel animate-fade-in">
      <h2>مرحباً بك في EduMind 🧪</h2>
      <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>
        مدرس الكيمياء الذكي الخاص بك.
      </p>
      
      <div style={{ marginTop: '2rem', display: 'grid', gap: '1rem', gridTemplateColumns: '1fr 1fr' }}>
        <div className="glass-panel" style={{ padding: '1rem' }}>
          <h4>حالة الخادم</h4>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
            <span style={{ 
              display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', 
              backgroundColor: health === 'healthy' ? '#10b981' : '#ef4444' 
            }} className={health === 'healthy' ? 'pulse-glow' : ''}></span>
            <span>{health === 'healthy' ? 'متصل' : health}</span>
          </div>
        </div>
        
        <div className="glass-panel" style={{ padding: '1rem' }}>
          <h4>التقدم الحالي</h4>
          <p className="text-gradient" style={{ fontSize: '1.5rem', fontWeight: 700, marginTop: '0.5rem' }}>75%</p>
        </div>
      </div>
      
      <div style={{ marginTop: '2rem' }}>
        <Link to="/chat" className="btn-primary" style={{ textDecoration: 'none' }}>
          ابدأ المحادثة
        </Link>
      </div>
    </div>
  );
};

type ChatMessage = {
  role: 'user' | 'assistant' | 'system';
  content: string;
  result?: ChatAnswer;
};

const ANSWER_TYPE_OPTIONS: Array<{ value: PreferredAnswerType; label: string }> = [
  { value: 'auto', label: 'تلقائي' },
  { value: 'text', label: 'نص' },
  { value: 'image', label: 'صورة' },
  { value: 'video', label: 'فيديو' },
  { value: 'mixed', label: 'مختلط' },
];

const renderAnswerBlock = (block: AnswerBlock, index: number) => {
  const key = `${block.type}-${block.page ?? 'none'}-${index}`;

  if (block.type === 'equation') {
    return (
      <div key={key} className="equation-block" dir="ltr">
        {block.content}
      </div>
    );
  }

  if (block.type === 'source_page' || block.type === 'image') {
    const imageUrl = resolveMediaUrl(block.image_url);
    if (!imageUrl) return null;
    return (
      <a key={key} className="source-page-thumb" href={imageUrl} target="_blank" rel="noreferrer">
        <img src={imageUrl} alt={`صفحة ${block.page ?? ''}`} loading="lazy" />
        <span>صفحة {block.page ?? '-'}</span>
      </a>
    );
  }

  if (block.type === 'video_script') {
    return (
      <div key={key} className="video-script-card">
        {block.content}
      </div>
    );
  }

  if (block.type === 'clarification') {
    return (
      <div key={key} className="clarification-card">
        {block.content}
      </div>
    );
  }

  if (block.type === 'table') {
    return (
      <pre key={key} className="table-block">
        {block.content}
      </pre>
    );
  }

  return <p key={key}>{block.content}</p>;
};

const Chat = () => {
  const [question, setQuestion] = useState('ما هي المعادلة الكيميائية للنحاس مع حمض الكبريت الممدد؟');
  const [answerType, setAnswerType] = useState<PreferredAnswerType>('auto');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'مرحباً! اكتب سؤالاً من كيمياء الصف التاسع وسأجيب اعتماداً على المقاطع المتاحة من الكتاب.',
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const sendQuestion = async () => {
    const text = question.trim();
    if (!text || loading) return;

    setLoading(true);
    setError('');
    setQuestion('');
    setMessages((current) => [...current, { role: 'user', content: text }]);

    try {
      const result = await askChemistry(text, answerType);
      setMessages((current) => [
        ...current,
        {
          role: 'assistant',
          content: result.answer,
          result,
        },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'تعذر الاتصال بالخادم';
      setError(message);
      setMessages((current) => [
        ...current,
        {
          role: 'system',
          content: 'حدث خطأ أثناء إرسال السؤال. تأكد أن backend يعمل على المنفذ 8000.',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel animate-fade-in chat-shell">
      <header className="chat-header">
        <h3>مدرس الكيمياء</h3>
        <span>{loading ? 'يفكر...' : 'جاهز'}</span>
      </header>

      <div className="chat-messages">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-message ${message.role}`}>
            {message.result?.blocks?.length ? (
              <div className="answer-blocks">
                {message.result.blocks.map((block, blockIndex) => renderAnswerBlock(block, blockIndex))}
              </div>
            ) : (
              <p>{message.content}</p>
            )}
            {message.result && (
              <div className="source-strip">
                <span>{message.result.answer_type}</span>
                <span>الثقة: {Math.round(message.result.confidence * 100)}%</span>
                {message.result.page_numbers.length > 0 && (
                  <span>الصفحات: {message.result.page_numbers.join(', ')}</span>
                )}
                {message.result.sources.slice(0, 3).map((source) => (
                  <span key={source.chunk_id}>
                    صفحة {source.page_number ?? '-'} · {source.content_type}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {error && <div className="chat-error">{error}</div>}

      <div className="chat-controls-row">
        <label className="answer-type-selector">
          <span>نوع الإجابة</span>
          <select
            value={answerType}
            onChange={(event) => setAnswerType(event.target.value as PreferredAnswerType)}
            disabled={loading}
          >
            {ANSWER_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="chat-input-row">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              sendQuestion();
            }
          }}
          placeholder="اكتب سؤالك هنا..."
          rows={2}
        />
        <button className="btn-primary" onClick={sendQuestion} disabled={loading || !question.trim()}>
          {loading ? '...' : 'إرسال'}
        </button>
      </div>
    </div>
  );
};

const Admin = () => (
  <div className="glass-panel animate-fade-in">
    <h3>لوحة التحكم (Admin) ⚙️</h3>
    <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>إدارة محتوى الكتب والأسئلة والطلاب.</p>
  </div>
);

function App() {
  return (
    <Router>
      <div className="app-container" dir="rtl">
        <aside className="glass-panel" style={{ height: 'fit-content' }}>
          <h1 className="text-gradient" style={{ marginBottom: '2rem', fontSize: '1.8rem' }}>EduMind</h1>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <Link to="/" className="btn-outline" style={{ textAlign: 'center', textDecoration: 'none' }}>الرئيسية</Link>
            <Link to="/chat" className="btn-outline" style={{ textAlign: 'center', textDecoration: 'none' }}>المحادثة</Link>
            <Link to="/admin" className="btn-outline" style={{ textAlign: 'center', textDecoration: 'none' }}>لوحة الإدارة</Link>
          </nav>
        </aside>
        
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/admin" element={<Admin />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
