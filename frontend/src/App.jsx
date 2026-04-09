import { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import PdfUpload from './components/PdfUpload';

function App() {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);

  function handleUploadComplete(uploadInfo) {
    const names = uploadInfo.filenames?.length ? uploadInfo.filenames : [uploadInfo.filename];
    setUploadedFiles((prev) => {
      const next = [...prev];
      names.forEach((name) => {
        if (!next.includes(name)) {
          next.unshift(name);
        }
      });
      return next;
    });
    if (names[0]) {
      setActiveFile(names[0]);
    }
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
                <li
                  key={`${name}-${idx}`}
                  title={name}
                  className={activeFile === name ? 'active' : ''}
                  onClick={() => setActiveFile(name)}
                >
                  {name}
                </li>
              ))}
            </ul>
          )}
        </section>
      </aside>

      <section className="chat-main">
        <ChatWindow activeFile={activeFile} uploadedFiles={uploadedFiles} />
      </section>
    </main>
  );
}

export default App;
