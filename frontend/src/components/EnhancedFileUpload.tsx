import React, { useState, useRef } from 'react';
import { filesAPI } from '../services/api';

interface EnhancedFileUploadProps {
  onUploadComplete: () => void;
}

const EnhancedFileUpload: React.FC<EnhancedFileUploadProps> = ({ onUploadComplete }) => {
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
      // Auto-populate name if empty
      if (!customName) {
        setCustomName(file.name);
      }
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      alert('Please select a file');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('name', customName.trim() || selectedFile.name);
      
      await filesAPI.upload(formData);
      onUploadComplete();
      setUploadProgress(100);
      
      // Reset form
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
    <div className="enhanced-file-upload">
      <h3>Upload File</h3>
      
      {!selectedFile ? (
        <div
          className={`upload-zone ${isDragging ? 'dragging' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="upload-icon">📁</div>
          <p>Drag and drop files here or</p>
          <button 
            onClick={handleButtonClick}
            className="upload-button"
          >
            Choose File
          </button>
        </div>
      ) : (
        <div className="upload-form">
          <div className="selected-file">
            <strong>Selected File:</strong> {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
          </div>
          
          <div className="form-group">
            <label>Display Name (optional):</label>
            <input
              type="text"
              placeholder="My Document"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              className="name-input"
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
              <button 
                onClick={handleUpload}
                className="btn-upload"
              >
                Upload File
              </button>
              <button 
                onClick={() => {
                  setSelectedFile(null);
                  setCustomName('');
                }}
                className="btn-cancel"
              >
                Cancel
              </button>
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

export default EnhancedFileUpload;