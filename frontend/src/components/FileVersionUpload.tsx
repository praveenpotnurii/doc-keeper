import React, { useState, useRef } from 'react';
import { filesAPI } from '../services/api';

interface FileVersionUploadProps {
  existingFileUrl: string;
  fileName: string;
  onUploadComplete: () => void;
  onCancel: () => void;
}

const FileVersionUpload: React.FC<FileVersionUploadProps> = ({
  existingFileUrl,
  fileName,
  onUploadComplete,
  onCancel
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (files: FileList) => {
    if (files.length > 0) {
      uploadNewVersion(files[0]);
    }
  };

  const uploadNewVersion = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('url', existingFileUrl);
      formData.append('name', fileName);
      
      // Use PUT method to update existing file with new version
      await filesAPI.uploadNewVersion(existingFileUrl, file);
      onUploadComplete();
      setUploadProgress(100);
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 1000);
    } catch (err: any) {
      alert('Failed to upload new version: ' + (err.response?.data?.detail || 'Unknown error'));
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    handleFileSelect(files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFileSelect(e.target.files);
    }
  };

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal version-upload-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Upload New Version</h3>
          <button className="close-btn" onClick={onCancel}>×</button>
        </div>
        
        <div className="modal-content">
          <p>Upload a new version of: <strong>{fileName}</strong></p>
          
          <div
            className={`upload-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            {isUploading ? (
              <div className="upload-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p>Uploading new version... {uploadProgress}%</p>
              </div>
            ) : (
              <>
                <div className="upload-icon">📁</div>
                <p>Drag and drop new file here or</p>
                <button 
                  onClick={handleButtonClick}
                  className="upload-button"
                  disabled={isUploading}
                >
                  Choose File
                </button>
              </>
            )}
          </div>
          
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileInputChange}
            style={{ display: 'none' }}
          />
        </div>
        
        <div className="modal-footer">
          <button onClick={onCancel} className="btn-cancel">Cancel</button>
        </div>
      </div>
    </div>
  );
};

export default FileVersionUpload;