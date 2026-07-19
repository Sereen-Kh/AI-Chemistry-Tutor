import { Children, type ReactNode } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FormattedText } from './DesignSystem';

const formatChemistryText = (children: ReactNode): ReactNode => (
  Children.map(children, (child) => (
    typeof child === 'string' ? <FormattedText text={child} /> : child
  ))
);

const safeExternalUrl = (href?: string): string | undefined => {
  if (!href) return undefined;
  try {
    const parsed = new URL(href);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? parsed.toString() : undefined;
  } catch {
    return undefined;
  }
};

const markdownComponents: Components = {
  p: ({ children }) => <p>{formatChemistryText(children)}</p>,
  h1: ({ children }) => <h2>{formatChemistryText(children)}</h2>,
  h2: ({ children }) => <h3>{formatChemistryText(children)}</h3>,
  h3: ({ children }) => <h4>{formatChemistryText(children)}</h4>,
  h4: ({ children }) => <h4>{formatChemistryText(children)}</h4>,
  li: ({ children }) => <li>{formatChemistryText(children)}</li>,
  strong: ({ children }) => <strong>{formatChemistryText(children)}</strong>,
  em: ({ children }) => <em>{formatChemistryText(children)}</em>,
  code: ({ children, className }) => (
    <code className={className} dir="ltr">{children}</code>
  ),
  pre: ({ children }) => <pre dir="ltr">{children}</pre>,
  a: ({ children, href }) => {
    const safeHref = safeExternalUrl(href);
    return safeHref ? (
      <a href={safeHref} target="_blank" rel="noopener noreferrer">
        {formatChemistryText(children)}
      </a>
    ) : <span>{formatChemistryText(children)}</span>;
  },
};

export const MarkdownAnswer = ({ text }: { text: string }) => (
  <div className="markdown-answer" dir="rtl">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={markdownComponents}
      skipHtml
    >
      {text}
    </ReactMarkdown>
  </div>
);
