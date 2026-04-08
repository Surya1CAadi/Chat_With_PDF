import { useMemo, useState } from 'react';
import { askQuestion } from '../api';

const QUICK_PROMPTS = [
  'Summarize this PDF in 5 bullets',
  'What are the key takeaways?',
  'List important dates and names',
  'Give me an executive summary',
];

function ChatWindow({ onClearChat }) {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [messages, setMessages] = useState([]);

  const sessionId = useMemo(() => crypto.randomUUID(), []);

  async function handleSend(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMessage = { role: 'user', text: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    try {
      setIsLoading(true);
      const response = await askQuestion(trimmed, sessionId);

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: response.answer,
          answerProvider: response.answer_provider,
          sources: response.sources || [],
        },
      ]);
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
    onClearChat?.();
  }

  return (
    <div className="chat-panel">
      <div className="chat-topbar">
        <h2>Ask anything about your uploaded PDF</h2>
        {/* <button className="ghost-button" type="button" onClick={handleClear} disabled={isLoading && messages.length === 0}>
          New chat
        </button> */}
      </div>

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
            <small>Answers are grounded in indexed chunks.</small>
            <button type="submit" disabled={isLoading || !input.trim()}>
              {isLoading ? 'Thinking...' : 'Send'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

export default ChatWindow;
