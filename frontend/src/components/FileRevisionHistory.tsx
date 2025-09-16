import React, { useState, useEffect } from 'react';
import { filesAPI, FileDocument, FileRevision } from '../services/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose, DialogBody, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { Download, Clock, FileText } from 'lucide-react';

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
      
      console.log('Raw revision data received:', revisionData);
      
      // Handle the response structure: {document: {...}, revisions: Array}
      if (Array.isArray(revisionData)) {
        // Direct array response
        console.log('Setting revisions (direct array):', revisionData);
        setRevisions(revisionData);
      } else if (revisionData && Array.isArray(revisionData.revisions)) {
        // Nested response with revisions property
        console.log('Setting revisions (nested):', revisionData.revisions);
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
      console.log('Downloading revision:', {
        fileUrl: file.url,
        revisionNumber: revision.revision_number,
        revisionId: revision.id,
        fileName: file.name
      });
      
      // Download specific revision using revision number
      const response = await filesAPI.download(file.url, revision.revision_number);
      
      console.log('Download response received:', {
        status: response.status,
        headers: response.headers,
        dataSize: response.data.size,
        contentType: response.headers['content-type']
      });
      
      console.log('All response headers:', Object.keys(response.headers));
      
      // Get the filename from Content-Disposition header if available
      // Try different header name variations
      const contentDisposition = response.headers['content-disposition'] || 
                                response.headers['Content-Disposition'];
      let downloadFilename = `${file.name}_v${revision.revision_number}`;
      
      console.log('Content-Disposition header:', contentDisposition);
      
      if (contentDisposition) {
        // Try to extract filename from header like 'attachment; filename="Assignment2.zip"'
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=["']?([^"';]+)["']?/);
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1];
          console.log('Extracted filename from header:', downloadFilename);
        }
      } else {
        // Fallback: generate filename based on content-type and revision
        const contentType = response.headers['content-type'];
        if (contentType === 'application/zip') {
          downloadFilename = `${file.name.replace(/\.[^/.]+$/, '')}_v${revision.revision_number}.zip`;
        } else if (contentType === 'application/pdf') {
          downloadFilename = `${file.name.replace(/\.[^/.]+$/, '')}_v${revision.revision_number}.pdf`;
        }
        console.log('Using fallback filename based on content-type:', downloadFilename);
      }
      
      console.log('Using filename:', downloadFilename);
      
      // Create blob with correct content type
      const contentType = response.headers['content-type'] || 'application/octet-stream';
      const blob = new Blob([response.data], { type: contentType });
      
      console.log('Created blob:', {
        size: blob.size,
        type: blob.type
      });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', downloadFilename);
      
      // Force download by clicking in a clean way
      document.body.appendChild(link);
      link.style.display = 'none';
      link.click();
      
      // Clean up
      setTimeout(() => {
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
      }, 100);
      
    } catch (err) {
      console.error('Download error:', err);
      alert('Failed to download revision');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const isLatestRevision = (revision: FileRevision) => {
    return file.latest_revision?.id === revision.id;
  };

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Revision History - {file.name}
          </DialogTitle>
          <DialogClose onClose={onClose} />
        </DialogHeader>
        
        <DialogBody>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-muted-foreground">Loading revision history...</p>
            </div>
          ) : error ? (
            <div className="bg-destructive/15 text-destructive text-sm p-3 rounded-md">
              {error}
            </div>
          ) : !Array.isArray(revisions) || revisions.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">No revisions found.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {revisions.map((revision) => (
                <div key={revision.id} className={`border rounded-lg p-4 flex items-center justify-between ${
                  isLatestRevision(revision) 
                    ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950' 
                    : 'border-border'
                }`}>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold">Version {revision.revision_number}</span>
                      {isLatestRevision(revision) && (
                        <span className="inline-flex items-center px-2 py-1 rounded-full bg-green-100 text-green-800 text-xs font-medium dark:bg-green-900 dark:text-green-200">
                          Latest
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{revision.formatted_file_size}</span>
                      <span className="inline-flex items-center px-2 py-1 rounded-full bg-secondary text-secondary-foreground text-xs">
                        {revision.file_extension}
                      </span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatDate(revision.uploaded_at)}
                      </span>
                    </div>
                  </div>
                  <Button 
                    onClick={() => handleDownloadRevision(revision)}
                    variant="outline"
                    size="sm"
                  >
                    <Download className="h-4 w-4 mr-1" />
                    Download
                  </Button>
                </div>
              ))}
            </div>
          )}
        </DialogBody>
        
        <DialogFooter>
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default FileRevisionHistory;