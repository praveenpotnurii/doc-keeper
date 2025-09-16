import React, { useState, useEffect } from 'react';
import { filesAPI, FileDocument, FileListResponse } from '../services/api';
import FileRevisionHistory from './FileRevisionHistory';
import FileVersionUpload from './FileVersionUpload';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Download, Upload, History, Trash2, FileText, Clock } from 'lucide-react';

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
      // Download latest version (explicitly specify latest revision number)
      const latestRevisionNumber = file.latest_revision?.revision_number;
      const response = await filesAPI.download(file.url, latestRevisionNumber);
      
      // Get the filename from Content-Disposition header if available
      const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
      let downloadFilename = file.name;
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=["']?([^"';]+)["']?/);
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1];
        }
      } else {
        // Fallback: generate filename based on content-type and latest revision info
        const contentType = response.headers['content-type'];
        const baseFileName = file.name.replace(/\.[^/.]+$/, ''); // Remove extension
        
        if (contentType === 'application/zip') {
          downloadFilename = `${baseFileName}.zip`;
        } else if (contentType === 'application/pdf') {
          downloadFilename = `${baseFileName}.pdf`;
        } else if (file.latest_revision?.file_extension) {
          // Use the extension from latest revision info
          downloadFilename = `${baseFileName}${file.latest_revision.file_extension}`;
        }
      }
      
      // Create blob with correct content type
      const contentType = response.headers['content-type'] || 'application/octet-stream';
      const blob = new Blob([response.data], { type: contentType });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', downloadFilename);
      
      document.body.appendChild(link);
      link.style.display = 'none';
      link.click();
      
      // Clean up
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      
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

  if (isLoading) return (
    <div className="flex items-center justify-center p-8">
      <p className="text-muted-foreground">Loading files...</p>
    </div>
  );
  
  if (error) return (
    <div className="bg-destructive/15 text-destructive text-sm p-3 rounded-md">
      {error}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <FileText className="h-6 w-6" />
        <h2 className="text-2xl font-semibold">Your Files</h2>
      </div>
      
      {!Array.isArray(files) || files.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">No files uploaded yet.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {files.map((file) => (
            <Card key={file.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1 flex-1 mr-2">
                    <CardTitle className="text-base line-clamp-2">{file.name}</CardTitle>
                    <CardDescription className="flex items-center gap-4 text-xs">
                      <span className="inline-flex items-center px-2 py-1 rounded-full bg-secondary text-secondary-foreground">
                        {file.latest_revision?.file_extension || 'unknown'}
                      </span>
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>{file.latest_revision?.formatted_file_size || '0 Bytes'}</span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {new Date(file.updated_at).toLocaleDateString()}
                  </span>
                </div>
                
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    v{file.latest_revision?.revision_number || 1}
                  </span>
                  <span className="text-muted-foreground">
                    {file.revision_count} revision{file.revision_count !== 1 ? 's' : ''}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-2">
                  <Button 
                    onClick={() => handleDownload(file)}
                    variant="outline"
                    size="sm"
                    className="w-full"
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Download
                  </Button>
                  <Button 
                    onClick={() => handleShowVersionUpload(file)}
                    variant="outline"
                    size="sm"
                    className="w-full"
                  >
                    <Upload className="h-4 w-4 mr-1" />
                    Version
                  </Button>
                  <Button 
                    onClick={() => handleShowRevisionHistory(file)}
                    variant="outline"
                    size="sm"
                    className="w-full"
                  >
                    <History className="h-4 w-4 mr-1" />
                    History
                  </Button>
                  <Button 
                    onClick={() => handleDelete(file)}
                    variant="destructive"
                    size="sm"
                    className="w-full"
                  >
                    <Trash2 className="h-4 w-4 mr-1" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
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