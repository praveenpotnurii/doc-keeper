import React, { useState, useEffect } from 'react';
import { filesAPI, FileDocument, FileListResponse } from '../services/api';
import FileRevisionHistory from './FileRevisionHistory';
import FileVersionUpload from './FileVersionUpload';

const FileList: React.FC = () => {
  const [files, setFiles] = useState<FileDocument[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedFile, setSelectedFile] = useState<FileDocument | null>(null);
  const [showRevisionHistory, setShowRevisionHistory] = useState(false);
  const [showVersionUpload, setShowVersionUpload] = useState(false);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      const response = await filesAPI.list();
      const fileData: FileListResponse | FileDocument[] = response.data;
      // Handle both direct array and paginated response
      if (Array.isArray(fileData)) {
        setFiles(fileData);
      } else if (fileData && 'results' in fileData && Array.isArray(fileData.results)) {
        setFiles(fileData.results);
      } else {
        setFiles([]);
      }
    } catch (err: any) {
      console.error('Error loading files:', err);
      setError('Failed to load files');
      setFiles([]); // Ensure files is always an array
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async (file: FileDocument) => {
    try {
      const response = await filesAPI.download(file.url);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file.name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download file');
    }
  };

  const handleDelete = async (file: FileDocument) => {
    if (!window.confirm(`Are you sure you want to delete ${file.name}?`)) {
      return;
    }

    try {
      await filesAPI.delete(file.url);
      setFiles(files.filter(f => f.id !== file.id));
    } catch (err) {
      alert('Failed to delete file');
    }
  };

  const handleShowRevisionHistory = (file: FileDocument) => {
    setSelectedFile(file);
    setShowRevisionHistory(true);
  };

  const handleCloseRevisionHistory = () => {
    setShowRevisionHistory(false);
    setSelectedFile(null);
  };

  const handleShowVersionUpload = (file: FileDocument) => {
    setSelectedFile(file);
    setShowVersionUpload(true);
  };

  const handleCloseVersionUpload = () => {
    setShowVersionUpload(false);
    setSelectedFile(null);
  };

  const handleVersionUploadComplete = () => {
    setShowVersionUpload(false);
    setSelectedFile(null);
    loadFiles(); // Refresh the file list
  };

  if (isLoading) return <div className="loading">Loading files...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="file-list">
      <h2>Your Files</h2>
      {!Array.isArray(files) || files.length === 0 ? (
        <p>No files uploaded yet.</p>
      ) : (
        <div className="files-grid">
          {files.map((file) => (
            <div key={file.id} className="file-card">
              <div className="file-header">
                <h3 className="file-name">{file.name}</h3>
                <span className="file-type">
                  {file.latest_revision?.file_extension || 'unknown'}
                </span>
              </div>
              <div className="file-info">
                <span className="file-size">
                  {file.latest_revision?.formatted_file_size || '0 Bytes'}
                </span>
                <span className="file-date">
                  {new Date(file.updated_at).toLocaleDateString()}
                </span>
                <span className="file-version">
                  v{file.latest_revision?.revision_number || 1}
                </span>
                <span className="file-revisions">
                  {file.revision_count} revision{file.revision_count !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="file-actions">
                <button 
                  onClick={() => handleDownload(file)}
                  className="btn-download"
                >
                  Download
                </button>
                <button 
                  onClick={() => handleShowVersionUpload(file)}
                  className="btn-version"
                >
                  New Version
                </button>
                <button 
                  onClick={() => handleShowRevisionHistory(file)}
                  className="btn-history"
                >
                  History
                </button>
                <button 
                  onClick={() => handleDelete(file)}
                  className="btn-delete"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {showRevisionHistory && selectedFile && (
        <FileRevisionHistory 
          file={selectedFile}
          onClose={handleCloseRevisionHistory}
        />
      )}
      
      {showVersionUpload && selectedFile && (
        <FileVersionUpload
          existingFileUrl={selectedFile.url}
          fileName={selectedFile.name}
          onUploadComplete={handleVersionUploadComplete}
          onCancel={handleCloseVersionUpload}
        />
      )}
    </div>
  );
};

export default FileList;