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

export const OsInstallerList: React.FC = () => {
  const [files, setFiles] = useState<OSFile[]>([]);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    fetchFiles();
    fetchStorageInfo();
  }, []);

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/os-installers/files`);
      if (res.ok) {
        const data = await res.json();
        setFiles(data.files || []);
      }
    } catch (error) {
      console.error('Failed to fetch OS installer files:', error);
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
    await fetchFiles();
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
      await fetchFiles();
      await fetchStorageInfo();
    } catch (error) {
      console.error('Failed to delete file:', error);
      alert('Error deleting file: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="os-installer-list">
      <div className="card mb-3">
        <div className="card-title">
          🖥️ Available operating system installers for PXE boot and cloud installations
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
      ) : files.length === 0 ? (
        <div className="card mt-4">
          <div className="empty-state">
            <div className="empty-state-icon">📦</div>
            <h3>No OS installers yet</h3>
            <p>Upload operating system installers to make them available for provisioning</p>
          </div>
        </div>
      ) : (
        <table style={{ marginTop: '24px' }}>
          <thead>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th>Modified</th>
              <th style={{ width: '100px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((file) => (
              <tr key={file.path}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span>📄</span>
                    <div>
                      <div style={{ fontWeight: '500' }}>{file.filename}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        {file.path}
                      </div>
                    </div>
                  </div>
                </td>
                <td>{formatBytes(file.size_bytes)}</td>
                <td style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                  {formatDate(file.modified_at)}
                </td>
                <td>
                  <button
                    className="btn-danger btn-small"
                    onClick={() => handleDeleteFile(file.path)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

