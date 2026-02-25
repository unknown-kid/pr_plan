import React, { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Typography } from 'antd';

const { Text, Paragraph } = Typography;

interface MarkdownRendererProps {
  content: string;
  style?: React.CSSProperties;
  className?: string;
}

/**
 * Convert LaTeX delimiters to markdown math delimiters.
 * 
 * LLMs often output \(...\) for inline math and \[...\] for display math,
 * but remark-math only recognizes $...$ and $$...$$.
 */
function convertLatexDelimiters(text: string): string {
  // Display math: \[...\] -> $$...$$
  // Use a non-greedy match. Handle multiline with [\s\S].
  text = text.replace(/\\\[([\s\S]*?)\\\]/g, '$$$$$1$$$$');
  
  // Inline math: \(...\) -> $...$
  text = text.replace(/\\\(([\s\S]*?)\\\)/g, '$$$1$$');
  
  return text;
}

/**
 * Fix markdown tables where all rows are on a single line.
 * 
 * LLM streaming may produce:
 *   "| h1 | h2 | |---|---| | d1 | d2 |"
 * 
 * This needs to become:
 *   "| h1 | h2 |\n|---|---|\n| d1 | d2 |"
 */
function fixTableNewlines(text: string): string {
  const lines = text.split('\n');
  const result: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) {
      result.push(line);
      continue;
    }

    const parts = trimmed.split('|');
    const totalCells = parts.length - 2;

    if (totalCells <= 1) {
      result.push(line);
      continue;
    }

    const isSep = (s: string) => /^\s*:?-+:?\s*$/.test(s);

    let sepStart = -1;
    let sepEnd = -1;
    for (let i = 1; i <= totalCells; i++) {
      if (isSep(parts[i])) {
        if (sepStart === -1) sepStart = i;
        sepEnd = i;
      } else if (sepStart !== -1) {
        break;
      }
    }

    let colCount = -1;
    if (sepStart !== -1) {
      colCount = sepEnd - sepStart + 1;
    }

    if (colCount > 0 && totalCells % colCount === 0 && totalCells > colCount) {
      const rows: string[] = [];
      for (let i = 1; i <= totalCells; i += colCount) {
        const rowCells = parts.slice(i, i + colCount);
        rows.push('|' + rowCells.join('|') + '|');
      }
      result.push(...rows);
    } else {
      result.push(line);
    }
  }

  return result.join('\n');
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ 
  content, 
  style = {}, 
  className = '' 
}) => {
  const processedContent = useMemo(() => {
    let text = content || '';
    text = convertLatexDelimiters(text);
    text = fixTableNewlines(text);
    return text;
  }, [content]);

  return (
    <div className={`markdown-body ${className}`} style={style}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          h1: ({ children }) => (
            <h1 style={{ fontSize: 20, margin: '16px 0 8px', fontWeight: 600 }}>{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ fontSize: 18, margin: '14px 0 8px', fontWeight: 600 }}>{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ fontSize: 16, margin: '12px 0 6px', fontWeight: 600 }}>{children}</h3>
          ),
          h4: ({ children }) => (
            <h4 style={{ fontSize: 15, margin: '10px 0 6px', fontWeight: 600 }}>{children}</h4>
          ),
          p: ({ children }) => (
            <p style={{ margin: '8px 0', lineHeight: 1.7 }}>{children}</p>
          ),
          ul: ({ children }) => (
            <ul style={{ paddingLeft: 20, margin: '8px 0' }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ paddingLeft: 20, margin: '8px 0' }}>{children}</ol>
          ),
          li: ({ children }) => (
            <li style={{ margin: '4px 0', lineHeight: 1.6 }}>{children}</li>
          ),
          code: ({ className, children, ...props }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code 
                  style={{ 
                    background: '#f5f5f5', 
                    padding: '2px 6px', 
                    borderRadius: 4, 
                    fontSize: 13,
                    fontFamily: 'Monaco, Menlo, Consolas, monospace',
                    color: '#c7254e'
                  }}
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <pre 
                style={{ 
                  background: '#f6f8fa', 
                  padding: '12px 16px', 
                  borderRadius: 6, 
                  overflow: 'auto',
                  fontSize: 13,
                  lineHeight: 1.5,
                  margin: '8px 0'
                }}
              >
                <code style={{ fontFamily: 'Monaco, Menlo, Consolas, monospace' }} {...props}>
                  {children}
                </code>
              </pre>
            );
          },
          blockquote: ({ children }) => (
            <blockquote 
              style={{ 
                borderLeft: '4px solid #1890ff', 
                paddingLeft: 16, 
                margin: '12px 0',
                color: '#666',
                background: '#f9f9f9',
                padding: '8px 16px',
                borderRadius: '0 4px 4px 0'
              }}
            >
              {children}
            </blockquote>
          ),
          strong: ({ children }) => (
            <strong style={{ fontWeight: 600 }}>{children}</strong>
          ),
          em: ({ children }) => (
            <em style={{ fontStyle: 'italic' }}>{children}</em>
          ),
          a: ({ href, children }) => (
            <a 
              href={href} 
              target="_blank" 
              rel="noopener noreferrer" 
              style={{ color: '#1890ff', textDecoration: 'none' }}
            >
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div style={{ overflow: 'auto', margin: '12px 0' }}>
              <table style={{ 
                borderCollapse: 'collapse', 
                width: '100%',
                fontSize: 14
              }}>
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead style={{ background: '#fafafa' }}>{children}</thead>
          ),
          th: ({ children }) => (
            <th style={{ 
              border: '1px solid #e8e8e8', 
              padding: '8px 12px', 
              textAlign: 'left',
              fontWeight: 600
            }}>
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td style={{ 
              border: '1px solid #e8e8e8', 
              padding: '8px 12px' 
            }}>
              {children}
            </td>
          ),
          hr: () => (
            <hr style={{ border: 'none', borderTop: '1px solid #e8e8e8', margin: '16px 0' }} />
          ),
          img: ({ src, alt }) => (
            <img 
              src={src} 
              alt={alt} 
              style={{ maxWidth: '100%', borderRadius: 4, margin: '8px 0' }} 
            />
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  );
};

export default MarkdownRenderer;
