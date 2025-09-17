import React, { useState, useRef } from 'react';
import { filesAPI } from '../services/api';

interface FileUploadProps {
  onUploadComplete: () => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadComplete }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [customName, setCustomName] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (files: FileList) => {
    if (files.length > 0) {
      const file = files[0];
      setSelectedFile(file);
      // Keep display name empty - user must provide it manually
    }
  };

  const uploadFile = async () => {
    if (!selectedFile) {
      alert('Please select a file');
      return;
    }

    if (!customName.trim()) {
      alert('Please provide a display name for the file');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('name', customName.trim());
      await filesAPI.upload(formData);
      onUploadComplete();
      setUploadProgress(100);
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setSelectedFile(null);
        setCustomName('');
      }, 1000);
    } catch (err: any) {
      alert('Failed to upload file: ' + (err.response?.data?.detail || 'Unknown error'));
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
    <div className="file-upload">
      {!selectedFile ? (
        <div
          className={`upload-zone ${isDragging ? 'dragging' : ''} ${isUploading ? 'uploading' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="upload-icon">📁</div>
          <p>Drag and drop files here or</p>
          <button 
            onClick={handleButtonClick}
            className="upload-button"
            disabled={isUploading}
          >
            Choose File
          </button>
        </div>
      ) : (
        <div className="file-details">
          <div className="selected-file">
            <span>Selected: {selectedFile.name}</span>
            <button onClick={() => { setSelectedFile(null); setCustomName(''); }}>×</button>
          </div>
          <div className="name-input">
            <label>Display Name *</label>
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="Enter a display name for your file"
              required
            />
          </div>
          {isUploading ? (
            <div className="upload-progress">
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <p>Uploading... {uploadProgress}%</p>
            </div>
          ) : (
            <div className="upload-actions">
              <button onClick={uploadFile} className="upload-button">Upload</button>
              <button onClick={() => { setSelectedFile(null); setCustomName(''); }} className="cancel-button">Cancel</button>
            </div>
          )}
        </div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        onChange={handleFileInputChange}
        style={{ display: 'none' }}
      />
    </div>
  );
};

export default FileUpload;