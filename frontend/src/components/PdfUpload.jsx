import { useState } from 'react';
import { uploadPdf } from '../api';

function PdfUpload({ onUploadComplete }) {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');

  async function handleUpload(event) {
    event.preventDefault();
    if (!file) {
      setMessage('Please choose a PDF file first.');
      return;
    }

    try {
      setIsUploading(true);
      setMessage('Uploading and indexing...');
      const result = await uploadPdf(file);
      setMessage(`${result.filename} indexed (${result.total_chunks_added} chunks).`);
      onUploadComplete?.(result);
      setFile(null);
      event.target.reset();
    } catch (error) {
      setMessage(error.message);
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="panel upload-panel">
      <div className="panel-heading">
        <h2>Upload PDF</h2>
        <span className="count-pill subtle">PDF only</span>
      </div>
      <form onSubmit={handleUpload} className="upload-form">
        <label className={`dropzone ${isUploading ? 'disabled' : ''}`}>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={isUploading}
          />
          <div className="dropzone-copy">
            <strong>{file ? file.name : 'Choose a PDF to index'}</strong>
            <span>{file ? 'Ready to upload' : 'Click to browse or drag a file into the picker'}</span>
          </div>
        </label>

        <button type="submit" disabled={isUploading || !file} className="primary-button">
          {isUploading ? 'Processing...' : 'Upload & Index'}
        </button>
      </form>
      {message && <p className={`status-text ${message.toLowerCase().includes('error') ? 'error' : 'success'}`}>{message}</p>}
    </div>
  );
}

export default PdfUpload;
