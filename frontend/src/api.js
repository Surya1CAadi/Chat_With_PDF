const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function uploadPdf(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Upload failed');
  }
  return data;
}

export async function uploadPdfFromUrl(url) {
  const response = await fetch(`${API_BASE_URL}/upload-url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'URL upload failed');
  }
  return data;
}

export async function askQuestion(question, sessionId, options = {}) {
  const { sourceFilter, mode = 'original', role = 'default', compareSources = [] } = options;
  const payload = { question, session_id: sessionId };
  if (sourceFilter) {
    payload.source_filter = sourceFilter;
  }
  payload.mode = mode;
  payload.role = role;
  if (compareSources.length > 0) {
    payload.compare_sources = compareSources;
  }

  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Question request failed');
  }
  return data;
}

export async function askQuestionStream(question, sessionId, options, onChunk) {
  const { sourceFilter, mode = 'original', role = 'default', compareSources = [] } = options || {};
  const payload = {
    question,
    session_id: sessionId,
    mode,
    role,
    stream: true,
  };
  if (sourceFilter) {
    payload.source_filter = sourceFilter;
  }
  if (compareSources.length > 0) {
    payload.compare_sources = compareSources;
  }

  const response = await fetch(`${API_BASE_URL}/ask-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok || !response.body) {
    let detail = 'Streaming request failed';
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      // Ignore parse failures and use fallback message.
    }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let donePayload = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    for (const rawEvent of events) {
      const dataLine = rawEvent
        .split('\n')
        .find((line) => line.startsWith('data: '));
      if (!dataLine) continue;

      const payloadText = dataLine.slice(6);
      let eventData;
      try {
        eventData = JSON.parse(payloadText);
      } catch {
        continue;
      }

      if (eventData.type === 'chunk') {
        onChunk?.(eventData.content || '');
      }
      if (eventData.type === 'done') {
        donePayload = eventData;
      }
    }
  }

  return donePayload || { type: 'done', provider: 'ollama', sources: [] };
}
