import React, { useState, useEffect } from 'react';
import { filesAPI, FileDocument, FileRevision } from '../services/api';

interface FileRevisionHistoryProps {
  file: FileDocument;
  onClose: () => void;
}

const FileRevisionHistory: React.FC<FileRevisionHistoryProps> = ({ file, onClose }) => {
  const [revisions, setRevisions] = useState<FileRevision[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadRevisions();
  }, [file.url]);

  const loadRevisions = async () => {
    try {
      const response = await filesAPI.getRevisions(file.url);
      const revisionData = response.data;
      
      // Handle the response structure: {document: {...}, revisions: Array}
      if (Array.isArray(revisionData)) {
        // Direct array response
        setRevisions(revisionData);
      } else if (revisionData && Array.isArray(revisionData.revisions)) {
        // Nested response with revisions property
        setRevisions(revisionData.revisions);
      } else {
        console.error('Expected array or object with revisions property, got:', revisionData);
        setRevisions([]);
      }
    } catch (err: any) {
      console.error('Error loading revisions for URL:', file.url);
      console.error('Full error:', err);
      setError('Failed to load revision history');
      setRevisions([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadRevision = async (revision: FileRevision) => {
    try {
      // Download specific revision using revision ID in query param
      const response = await filesAPI.download(`${file.url}?revision=${revision.id}`);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${file.name}_v${revision.revision_number}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Failed to download revision');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const isLatestRevision = (revision: FileRevision) => {
    return file.latest_revision?.id === revision.id;
  };

  if (isLoading) {
    return (
      <div className="modal-overlay">
        <div className="modal">
          <div className="loading">Loading revision history...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="modal-overlay">
        <div className="modal">
          <div className="error">{error}</div>
          <button onClick={onClose}>Close</button>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal revision-history-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Revision History - {file.name}</h3>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-content">
          {!Array.isArray(revisions) || revisions.length === 0 ? (
            <p>No revisions found.</p>
          ) : (
            <div className="revision-list">
              {revisions.map((revision) => (
                <div key={revision.id} className={`revision-item ${isLatestRevision(revision) ? 'latest' : ''}`}>
                  <div className="revision-info">
                    <div className="revision-header">
                      <span className="revision-number">Version {revision.revision_number}</span>
                      {isLatestRevision(revision) && (
                        <span className="latest-badge">Latest</span>
                      )}
                    </div>
                    <div className="revision-details">
                      <span className="revision-size">{revision.formatted_file_size}</span>
                      <span className="revision-type">{revision.file_extension}</span>
                      <span className="revision-date">{formatDate(revision.uploaded_at)}</span>
                    </div>
                  </div>
                  <div className="revision-actions">
                    <button 
                      onClick={() => handleDownloadRevision(revision)}
                      className="btn-download-revision"
                    >
                      Download
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
        <div className="modal-footer">
          <button onClick={onClose} className="btn-close">Close</button>
        </div>
      </div>
    </div>
  );
};

export default FileRevisionHistory;