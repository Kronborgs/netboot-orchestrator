import React, { useState, useEffect } from 'react';
import { apiFetch } from '../api/client';

interface OSFile {
  filename: string;
  path: string;
  size_bytes: number;
  created_at: string;
  modified_at: string;
}

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

interface FolderNode {
  name: string;
  type: 'folder' | 'file';
  path: string;
  children?: FolderNode[];
  size_bytes: number;
  size_display?: string;
  created_at?: string;
  modified_at?: string;
}

const FolderItem: React.FC<{ node: FolderNode; level: number; onDelete: (path: string) => void }> = ({ 
  node, 
  level,
  onDelete 
}) => {
  const [expanded, setExpanded] = useState(level === 0);

  if (node.type === 'file') {
    return (
      <div style={{ 
        paddingLeft: `${level * 20 + 8}px`, 
        paddingRight: '8px',
        paddingTop: '8px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid var(--border-color)',
        minHeight: '32px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
          <span>📄</span>
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
            <span style={{ fontWeight: '500' }}>{node.name}</span>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              {node.size_display}
            </span>
          </div>
        </div>
        <button
          className="btn-danger btn-small"
          onClick={() => onDelete(node.path)}
          style={{ marginLeft: '12px' }}
        >
          Delete
        </button>
      </div>
    );
  }

  return (
    <div>
      <div style={{ 
        paddingLeft: `${level * 20}px`,
        paddingRight: '8px',
        paddingTop: '8px',
        paddingBottom: '8px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        cursor: 'pointer',
        backgroundColor: level % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
        borderBottom: level === 0 ? '1px solid var(--border-color)' : 'none'
      }}
      onClick={() => setExpanded(!expanded)}>
        <span style={{ 
          width: '20px', 
          display: 'flex',
          justifyContent: 'center',
          transition: 'transform 0.2s',
          transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)'
        }}>
          {node.children && node.children.length > 0 ? '▶' : ''}
        </span>
        <span style={{ fontSize: '16px' }}>📁</span>
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
          <span style={{ fontWeight: '500' }}>{node.name || 'root'}</span>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {node.size_display}
          </span>
        </div>
      </div>
      
      {expanded && node.children && (
        <div>
          {node.children.map((child, idx) => (
            <FolderItem 
              key={`${child.path}-${idx}`} 
              node={child} 
              level={level + 1}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const OsInstallerList: React.FC = () => {
  const [folderTree, setFolderTree] = useState<FolderNode | null>(null);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    fetchFolderTree();
    fetchStorageInfo();
  }, []);

  const fetchFolderTree = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/os-installers/tree`);
      if (res.ok) {
        const data = await res.json();
        setFolderTree(data.tree);
      }
    } catch (error) {
      console.error('Failed to fetch folder tree:', error);
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
    await fetchFolderTree();
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
      await fetchFolderTree();
      await fetchStorageInfo();
    } catch (error) {
      console.error('Failed to delete file:', error);
      alert('Error deleting file: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
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

      {loading ? (
        <div className="loading mt-4">
          <div className="spinner"></div>
        </div>
      ) : folderTree && folderTree.children && folderTree.children.length > 0 ? (
        <div className="card" style={{ background: 'var(--bg-secondary)' }}>
          <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
            {folderTree.children.map((child, idx) => (
              <FolderItem 
                key={`${child.path}-${idx}`} 
                node={child} 
                level={0}
                onDelete={handleDeleteFile}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="card mt-4">
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <h3>No files yet</h3>
            <p>Upload operating system installers using drag-and-drop or browse button</p>
          </div>
        </div>
      )}
    </div>
  );
};

