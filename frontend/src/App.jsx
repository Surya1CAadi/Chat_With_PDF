import { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import PdfUpload from './components/PdfUpload';

function App() {
  const [uploadedFiles, setUploadedFiles] = useState([]);

  function handleUploadComplete(uploadInfo) {
    setUploadedFiles((prev) => [uploadInfo.filename, ...prev]);
  }

  return (
    <main className="chatgpt-shell">
      <aside className="chat-sidebar">
        <div className="sidebar-brand">
          <h1>Chat with PDF</h1>
          <p>Local RAG assistant</p>
        </div>

        <div className="sidebar-block">
          <PdfUpload onUploadComplete={handleUploadComplete} />
        </div>

        <section className="sidebar-files">
          <div className="files-header">
            <h3>Session Files</h3>
            <span>{uploadedFiles.length}</span>
          </div>
          {uploadedFiles.length === 0 ? (
            <p className="placeholder compact">No files uploaded yet.</p>
          ) : (
            <ul className="file-list">
              {uploadedFiles.map((name, idx) => (
                <li key={`${name}-${idx}`} title={name}>
                  {name}
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>

      <section className="chat-main">
        <ChatWindow />
      </section>
    </main>
  );
}

export default App;
