import { useState } from 'react';
import { askQuestionStream } from '../api';

const QUICK_PROMPTS = [
  'Summarize this PDF in 5 bullets',
  'What are the key takeaways?',
  'List important dates and names',
  'Give me an executive summary',
];

const MODES = [
  { value: 'original', label: 'Original' },
  { value: 'summary', label: 'Summary' },
  { value: 'qa', label: 'Q&A' },
  { value: 'deep_analysis', label: 'Deep analysis' },
  { value: 'extract_data', label: 'Extract data' },
  { value: 'compare', label: 'Compare PDFs' },
];

function ChatWindow({ onClearChat, activeFile, uploadedFiles = [] }) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  const [mode, setMode] = useState('original');
  const [compareSources, setCompareSources] = useState([]);

  function mergeStreamChunk(currentText, incomingChunk) {
    if (!incomingChunk) return currentText;
    if (!currentText) return incomingChunk;

    // Some providers send cumulative chunks (full text-so-far) rather than token deltas.
    if (incomingChunk.startsWith(currentText)) {
      return incomingChunk;
    }

    // Skip exact or suffix duplicates when transport repeats the same chunk.
    if (currentText.endsWith(incomingChunk)) {
      return currentText;
    }

    // Merge by overlap for partially repeated chunks.
    const maxOverlap = Math.min(currentText.length, incomingChunk.length);
    for (let size = maxOverlap; size > 0; size -= 1) {
      if (currentText.slice(-size) === incomingChunk.slice(0, size)) {
        return currentText + incomingChunk.slice(size);
      }
    }

    return currentText + incomingChunk;
  }

  async function handleSend(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMessage = { role: 'user', text: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      setIsLoading(true);
      const options = {
        sourceFilter: mode === 'compare' ? null : activeFile,
        mode,
        role: 'default',
        compareSources: mode === 'compare' ? compareSources : [],
      };

      const assistantIndex = messages.length + 1;
      let streamedText = '';
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: '',
          answerProvider: 'ollama',
          sources: [],
        },
      ]);

      const donePayload = await askQuestionStream(trimmed, sessionId, options, (chunk) => {
        streamedText = mergeStreamChunk(streamedText, chunk);
        setMessages((prev) => {
          const cloned = [...prev];
          const target = cloned[assistantIndex];
          if (!target) return prev;
          target.text = streamedText;
          return cloned;
        });
      });

      setMessages((prev) => {
        const cloned = [...prev];
        const target = cloned[assistantIndex];
        if (!target) return prev;
        target.answerProvider = donePayload.provider || 'ollama';
        target.sources = donePayload.sources || [];
        return cloned;
      });
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: `Error: ${error.message}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  function handleQuickPrompt(prompt) {
    setInput(prompt);
  }

  function handleClear() {
    setMessages([]);
    setInput('');
    setSessionId(crypto.randomUUID());
    onClearChat?.();
  }

  function toggleCompareSource(fileName) {
    setCompareSources((prev) => {
      if (prev.includes(fileName)) {
        return prev.filter((item) => item !== fileName);
      }
      return [...prev, fileName].slice(0, 4);
    });
  }

  async function copyReply(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Ignore clipboard errors silently to avoid interrupting chat flow.
    }
  }

  function downloadReplyPdf(text) {
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br/>');
    const html = `
      <html>
        <head><title>Reply Export</title></head>
        <body style="font-family: Arial, sans-serif; padding: 24px;">${escaped}</body>
      </html>
    `;
    const printWindow = window.open('', '_blank');
    if (printWindow) {
      printWindow.document.write(html);
      printWindow.document.close();
      printWindow.focus();
      printWindow.print();
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-topbar">
        <h2>{activeFile ? `Asking: ${activeFile}` : 'Ask anything about your uploaded PDF'}</h2>
        <button className="ghost-button" type="button" onClick={handleClear} disabled={isLoading && messages.length === 0}>
          New chat
        </button>
      </div>

      <div className="chat-body">
        <div className="chat-thread">
          {mode === 'compare' && (
            <div className="compare-strip">
              <strong>Select files to compare:</strong>
              <div className="compare-files">
                {uploadedFiles.map((fileName) => (
                  <label key={fileName}>
                    <input
                      type="checkbox"
                      checked={compareSources.includes(fileName)}
                      onChange={() => toggleCompareSource(fileName)}
                    />
                    <span>{fileName}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          <div className="chat-messages">
        {messages.length === 0 && (
          <div className="empty-chat">
            <h3>How can I help?</h3>
            <div className="quick-prompts">
              {QUICK_PROMPTS.map((prompt) => (
                <button key={prompt} type="button" className="chip-button" onClick={() => handleQuickPrompt(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-bubble ${msg.role}`}>
            <div className="bubble-meta">
              <strong>{msg.role === 'user' ? 'You' : 'Assistant'}</strong>
              {msg.role === 'assistant' && msg.answerProvider && (
                <span className="provider-tag">via {msg.answerProvider}</span>
              )}
            </div>
            <p>{msg.text}</p>
            {msg.sources?.length > 0 && (
              <div className="sources">
                <small>Sources:</small>
                {msg.sources.slice(0, 3).map((source, sourceIdx) => (
                  <small key={sourceIdx}>
                    {source.source} (page {source.page || 'N/A'})
                  </small>
                ))}
              </div>
            )}
            {msg.role === 'assistant' && msg.text.trim().length > 0 && (
              <div className="reply-actions">
                <button type="button" className="ghost-button reply-action-btn" onClick={() => copyReply(msg.text)}>
                  Copy Reply
                </button>
                <button type="button" className="ghost-button reply-action-btn" onClick={() => downloadReplyPdf(msg.text)}>
                  Download PDF
                </button>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="typing-indicator">
            <span />
            <span />
            <span />
          </div>
        )}
          </div>

          <form className="chat-composer" onSubmit={handleSend}>
            <div className="composer-input-wrap">
              <textarea
                value={input}
                placeholder="Ask a question about your PDFs..."
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
                rows={3}
              />
              <div className="composer-footer">
                <div className="composer-mode">
                  <span>Mode</span>
                  <select value={mode} onChange={(e) => setMode(e.target.value)} disabled={isLoading}>
                    {MODES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </div>
                <button type="submit" disabled={isLoading || !input.trim()}>
                  {isLoading ? 'Thinking...' : 'Send'}
                </button>
              </div>
            </div>
          </form>
        </div>

      </div>
    </div>
  );
}

export default ChatWindow;
