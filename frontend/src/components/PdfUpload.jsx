import { useState } from 'react';
import { uploadPdf, uploadPdfFromUrl } from '../api';

function PdfUpload({ onUploadComplete }) {
  const [uploadType, setUploadType] = useState('file');
  const [files, setFiles] = useState([]);
  const [urlInput, setUrlInput] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');

  async function handleUpload(event) {
    event.preventDefault();
    try {
      setIsUploading(true);
      let result;

      if (uploadType === 'file') {
        if (!files.length) {
          setMessage('Please choose at least one PDF file first.');
          return;
        }
        setMessage('Uploading and indexing...');
        result = await uploadPdf(files);
        setFiles([]);
        event.target.reset();
      } else {
        const trimmedUrl = urlInput.trim();
        if (!trimmedUrl) {
          setMessage('Please enter a PDF URL first.');
          return;
        }
        setMessage('Downloading and indexing from URL...');
        result = await uploadPdfFromUrl(trimmedUrl);
        setUrlInput('');
      }

      const uploadedCount = result.total_files_uploaded || (result.filenames?.length ?? 1);
      if (uploadedCount > 1) {
        setMessage(`${uploadedCount} PDFs indexed (${result.total_chunks_added} chunks).`);
      } else {
        setMessage(`${result.filename} indexed (${result.total_chunks_added} chunks).`);
      }
      onUploadComplete?.(result);
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

      <div className="upload-type-toggle" role="tablist" aria-label="Upload source type">
        <button
          type="button"
          className={`ghost-button ${uploadType === 'file' ? 'active' : ''}`}
          onClick={() => setUploadType('file')}
          disabled={isUploading}
        >
          PDF
        </button>
        <button
          type="button"
          className={`ghost-button ${uploadType === 'url' ? 'active' : ''}`}
          onClick={() => setUploadType('url')}
          disabled={isUploading}
        >
          URL / Drive
        </button>
      </div>

      <form onSubmit={handleUpload} className="upload-form">
        {uploadType === 'file' ? (
          <label className={`dropzone ${isUploading ? 'disabled' : ''}`}>
            <input
              type="file"
              accept="application/pdf"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
              disabled={isUploading}
            />
            <div className="dropzone-copy">
              <strong>
                {files.length === 0
                  ? 'Choose PDF files to index'
                  : files.length === 1
                    ? files[0].name
                    : `${files.length} files selected`}
              </strong>
              <span>{files.length > 0 ? 'Ready to upload' : 'Click to browse or drag files into the picker'}</span>
            </div>
          </label>
        ) : (
          <div className="url-form">
            <input
              type="url"
              placeholder="Paste PDF URL or Google Drive share URL"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              disabled={isUploading}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={isUploading || (uploadType === 'file' ? files.length === 0 : !urlInput.trim())}
          className="primary-button"
        >
          {isUploading ? 'Processing...' : 'Upload & Index'}
        </button>
      </form>
      {message && <p className={`status-text ${message.toLowerCase().includes('error') ? 'error' : 'success'}`}>{message}</p>}
    </div>
  );
}

export default PdfUpload;
