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

export async function askQuestion(question, sessionId) {
  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question, session_id: sessionId }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || 'Question request failed');
  }
  return data;
}
