import React, { useState } from 'react';
import FileList from './FileList';
import EnhancedFileUpload from './EnhancedFileUpload';
import { useAuth } from '../contexts/AuthContext';

const Dashboard: React.FC = () => {
  const [refreshKey, setRefreshKey] = useState(0);
  const { user, logout } = useAuth();

  const handleUploadComplete = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Doc Keeper</h1>
          <div className="user-info">
            <span>Welcome, {user?.username}</span>
            <button onClick={logout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>
      
      <main className="dashboard-main">
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