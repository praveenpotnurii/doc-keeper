import React, { useState, useRef } from 'react';
import { filesAPI } from '../services/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose, DialogBody, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Upload, File } from 'lucide-react';

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
    <Dialog open={true} onOpenChange={(open) => !open && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload New Version
          </DialogTitle>
          <DialogClose onClose={onCancel} />
        </DialogHeader>
        
        <DialogBody>
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Upload a new version of: <span className="font-medium text-foreground">{fileName}</span>
            </p>
            
            <div
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragging 
                  ? 'border-primary bg-primary/5' 
                  : isUploading
                  ? 'border-muted-foreground/25 cursor-not-allowed'
                  : 'border-muted-foreground/25 hover:border-primary hover:bg-primary/5'
              }`}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={!isUploading ? handleButtonClick : undefined}
            >
              {isUploading ? (
                <div className="space-y-2">
                  <div className="w-full bg-muted rounded-full h-2">
                    <div 
                      className="bg-primary h-2 rounded-full transition-all duration-300" 
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Uploading new version... {uploadProgress}%
                  </p>
                </div>
              ) : (
                <>
                  <File className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
                  <p className="text-lg font-medium mb-2">Drop new file here</p>
                  <p className="text-sm text-muted-foreground mb-4">
                    or click to browse files
                  </p>
                  <Button variant="outline" disabled={isUploading}>
                    Choose File
                  </Button>
                </>
              )}
            </div>
            
            <input
              ref={fileInputRef}
              type="file"
              onChange={handleFileInputChange}
              className="hidden"
            />
          </div>
        </DialogBody>
        
        <DialogFooter>
          <Button onClick={onCancel} variant="outline" disabled={isUploading}>
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default FileVersionUpload;