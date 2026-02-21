import React, { useState, useEffect } from 'react';
import { apiFetch } from '../api/client';

interface StorageInfo {
  os_installers: {
    size_bytes: number;
    size_gb: number;
  };
  images: {
    size_bytes: number;
    size_gb: number;
  };
  total: {
    size_bytes: number;
    size_gb: number;
  };
}

interface FolderItem {
  name: string;
  type: 'folder' | 'file';
  path: string;
  size_bytes: number;
  size_display: string;
  has_children?: boolean;
  created_at?: string;
  modified_at?: string;
}

interface Breadcrumb {
  name: string;
  path: string;
}

export const OsInstallerList: React.FC = () => {
  const [currentFolder, setCurrentFolder] = useState<string>("");
  const [items, setItems] = useState<FolderItem[]>([]);
  const [breadcrumb, setBreadcrumb] = useState<Breadcrumb[]>([]);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    fetchFolderContents("");
    fetchStorageInfo();
  }, []);

  const fetchFolderContents = async (folderPath: string) => {
    setLoading(true);
    try {
      const query = folderPath ? `?folder_path=${encodeURIComponent(folderPath)}` : "";
      const res = await apiFetch(`/api/v1/os-installers/browse${query}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentFolder(data.path);
        setItems(data.items || []);
        setBreadcrumb(data.breadcrumb || []);
      }
    } catch (error) {
      console.error('Failed to fetch folder contents:', error);
    }
    setLoading(false);
  };

  const fetchStorageInfo = async () => {
    try {
      const res = await apiFetch(`/api/v1/storage/info`);
      if (res.ok) {
        setStorage(await res.json());
      }
    } catch (error) {
      console.error('Failed to fetch storage info:', error);
    }
  };

  const handleFolderClick = (folderPath: string) => {
    fetchFolderContents(folderPath);
  };

  const handleBreadcrumbClick = (path: string) => {
    fetchFolderContents(path);
  };

  const handleFileUpload = async (filesToUpload: FileList) => {
    if (!filesToUpload || filesToUpload.length === 0) return;

    setUploading(true);
    setUploadProgress(0);

    for (let i = 0; i < filesToUpload.length; i++) {
      const file = filesToUpload[i];
      const formData = new FormData();
      formData.append('file', file);

      try {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const percentComplete = Math.round((i * 100 + (e.loaded / e.total) * 100) / filesToUpload.length);
            setUploadProgress(percentComplete);
          }
        });

        await new Promise((resolve, reject) => {
          xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
              resolve(true);
            } else {
              reject(new Error(`Upload failed: ${xhr.status}`));
            }
          });
          xhr.addEventListener('error', reject);

          xhr.open('POST', `${window.location.protocol}//${window.location.hostname}:8000/api/v1/os-installers/upload`);
          xhr.send(formData);
        });
      } catch (error) {
        console.error(`Failed to upload ${file.name}:`, error);
      }
    }

    setUploading(false);
    setUploadProgress(0);
    await fetchFolderContents(currentFolder);
    await fetchStorageInfo();
  };

  const handleDeleteFile = async (filePath: string) => {
    if (!confirm('Are you sure you want to delete this file?')) return;

    try {
      const res = await apiFetch(`/api/v1/os-installers/files/${filePath}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        alert(`Failed to delete file: ${res.statusText}`);
        return;
      }
      await fetchFolderContents(currentFolder);
      await fetchStorageInfo();
    } catch (error) {
      console.error('Failed to delete file:', error);
      alert('Error deleting file: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const formatDateTime = (value?: string): string => {
    if (!value) return 'Unknown';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return 'Unknown';
    return parsed.toLocaleString();
  };

  return (
    <div className="os-installer-list">
      <div className="card mb-3">
        <div className="card-title">
          🖥️ Operating system installers & files
        </div>

        {storage && (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginBottom: '24px'
          }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>OS Installers</div>
              <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {storage.os_installers.size_gb.toFixed(2)} GB
              </div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Images</div>
              <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {storage.images.size_gb.toFixed(2)} GB
              </div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '8px' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Total</div>
              <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--primary-blue)' }}>
                {storage.total.size_gb.toFixed(2)} GB
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Upload Area */}
      <div
        className={`upload-area ${dragOver ? 'dragover' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFileUpload(e.dataTransfer.files);
        }}
      >
        <div style={{ fontSize: '32px', marginBottom: '8px' }}>📁</div>
        <div style={{ marginBottom: '8px' }}>
          <strong>Drag and drop OS installers here</strong>
        </div>
        <div style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '16px' }}>
          or
        </div>
        <label style={{ display: 'inline-block' }}>
          <input
            type="file"
            multiple
            onChange={(e) => handleFileUpload(e.target.files)}
            style={{ display: 'none' }}
            disabled={uploading}
          />
          <span className="btn-primary">Browse Files</span>
        </label>
      </div>

      {uploading && (
        <div className="card mt-4 mb-3" style={{ background: 'var(--bg-tertiary)' }}>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ marginBottom: '4px' }}>Uploading...</div>
            <div className="progress">
              <div 
                className="progress-bar"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
            <div style={{ textAlign: 'center', fontSize: '12px', color: 'var(--text-secondary)' }}>
              {uploadProgress}%
            </div>
          </div>
        </div>
      )}

      {/* Breadcrumb Navigation */}
      {breadcrumb.length > 0 && (
        <div className="card" style={{ background: 'var(--bg-tertiary)', marginBottom: '16px', padding: '12px 16px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', fontSize: '14px', flexWrap: 'wrap' }}>
            {breadcrumb.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <span style={{ color: 'var(--text-secondary)' }}>/</span>}
                <button
                  onClick={() => handleBreadcrumbClick(crumb.path)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: crumb.path === currentFolder ? 'var(--primary-blue)' : 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: '4px 8px',
                    textDecoration: crumb.path === currentFolder ? 'underline' : 'none',
                    fontWeight: crumb.path === currentFolder ? '600' : '400'
                  }}
                >
                  {crumb.name}
                </button>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Folder Contents */}
      {loading ? (
        <div className="loading mt-4">
          <div className="spinner"></div>
          <div style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>Loading folder contents...</div>
        </div>
      ) : items.length === 0 ? (
        <div className="card mt-4">
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <h3>Folder is empty</h3>
            <p>Upload files to this folder or navigate to another folder</p>
          </div>
        </div>
      ) : (
        <div className="card">
          <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
            {items.map((item, idx) => (
              <div
                key={idx}
                style={{
                  paddingLeft: '12px',
                  paddingRight: '12px',
                  paddingTop: '12px',
                  paddingBottom: '12px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderBottom: idx < items.length - 1 ? '1px solid var(--border-color)' : 'none',
                  minHeight: '48px',
                  cursor: item.type === 'folder' ? 'pointer' : 'default',
                  backgroundColor: item.type === 'folder' ? 'var(--bg-tertiary)' : 'transparent',
                  transition: 'background-color 0.2s'
                }}
                onClick={() => item.type === 'folder' && handleFolderClick(item.path)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, minWidth: 0 }}>
                  <span style={{ fontSize: '18px', flexShrink: 0 }}>
                    {item.type === 'folder' ? '📁' : '📄'}
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: '500', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {item.name}
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {item.size_display}
                      {item.type === 'folder' && item.has_children && ' • Click to open'}
                    </div>
                    {item.type === 'file' && (
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        Last changed: {formatDateTime(item.modified_at || item.created_at)}
                      </div>
                    )}
                  </div>
                </div>
                {item.type === 'file' && (
                  <button
                    className="btn-danger btn-small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteFile(item.path);
                    }}
                    style={{ marginLeft: '12px', flexShrink: 0 }}
                  >
                    Delete
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

