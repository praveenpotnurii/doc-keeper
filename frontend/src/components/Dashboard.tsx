import React, { useState } from 'react';
import FileList from './FileList';
import EnhancedFileUpload from './EnhancedFileUpload';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/button';
import { ThemeToggle } from './ui/theme-toggle';
import { LogOut } from 'lucide-react';

const Dashboard: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);
  const { user, logout } = useAuth();

  const handleUploadComplete = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <h1 className="text-xl font-semibold">Doc Keeper</h1>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              Welcome, {user?.username}
            </span>
            <ThemeToggle />
            <Button onClick={logout} variant="outline" size="sm">
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>
      
      <main className="container mx-auto px-4 py-8 space-y-8">
        <div className="upload-section">
          <EnhancedFileUpload onUploadComplete={handleUploadComplete} />
        </div>
        
        <div className="files-section">
          <FileList key={refreshKey} />
        </div>
      </main>
    </div>
  );
};

export default Dashboard;