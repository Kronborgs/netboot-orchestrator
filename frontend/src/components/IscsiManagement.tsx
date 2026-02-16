import React, { useState, useEffect } from 'react';
import { apiFetch } from '../api/client';

interface IscsiImage {
  id: string;
  name: string;
  size_gb: number;
  actual_size_gb?: number;
  device_type: string;
  assigned_to?: string;
  status: string;
  target_name?: string;
  file_exists?: boolean;
  created_at?: string;
  copied_from?: string;
}

interface Device {
  mac: string;
  name: string;
  device_type: string;
  image_id?: string;
}

export const IscsiManagement: React.FC = () => {
  const [images, setImages] = useState<IscsiImage[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [copying, setCopying] = useState<string | null>(null);
  const [copyName, setCopyName] = useState('');
  const [linking, setLinking] = useState<string | null>(null);
  const [linkMac, setLinkMac] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Create form
  const [newName, setNewName] = useState('');
  const [newSize, setNewSize] = useState(64);

  useEffect(() => {
    fetchImages();
    fetchDevices();
  }, []);

  useEffect(() => {
    if (success || error) {
      const t = setTimeout(() => { setSuccess(null); setError(null); }, 5000);
      return () => clearTimeout(t);
    }
  }, [success, error]);

  const fetchImages = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/boot/iscsi/images');
      if (res.ok) setImages(await res.json());
    } catch (e) {
      console.error('Failed to fetch iSCSI images:', e);
    }
    setLoading(false);
  };

  const fetchDevices = async () => {
    try {
      const res = await apiFetch('/api/v1/devices');
      if (res.ok) setDevices(await res.json());
    } catch (e) {
      console.error('Failed to fetch devices:', e);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const res = await apiFetch(`/api/v1/boot/iscsi/images?name=${encodeURIComponent(newName)}&size_gb=${newSize}`, { method: 'POST' });
      if (res.ok) {
        setSuccess(`Image "${newName}" (${newSize} GB) created successfully`);
        setNewName('');
        setNewSize(64);
        await fetchImages();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to create image');
      }
    } catch (e) {
      setError('Failed to create image');
    }
    setCreating(false);
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete iSCSI image "${name}"? This cannot be undone.`)) return;
    try {
      const res = await apiFetch(`/api/v1/boot/iscsi/images/${name}`, { method: 'DELETE' });
      if (res.ok) {
        setSuccess(`Image "${name}" deleted`);
        await fetchImages();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to delete');
      }
    } catch (e) {
      setError('Failed to delete image');
    }
  };

  const handleCopy = async () => {
    if (!copying || !copyName.trim()) return;
    try {
      const res = await apiFetch(`/api/v1/boot/iscsi/images/${copying}/copy?dest_name=${encodeURIComponent(copyName)}`, { method: 'POST' });
      if (res.ok) {
        setSuccess(`Image copied as "${copyName}"`);
        setCopying(null);
        setCopyName('');
        await fetchImages();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to copy');
      }
    } catch (e) {
      setError('Failed to copy image');
    }
  };

  const handleLink = async () => {
    if (!linking || !linkMac) return;
    try {
      const res = await apiFetch(`/api/v1/boot/iscsi/images/${linking}/link?mac=${encodeURIComponent(linkMac)}`, { method: 'POST' });
      if (res.ok) {
        setSuccess(`Image "${linking}" linked to ${linkMac}`);
        setLinking(null);
        setLinkMac('');
        await fetchImages();
        await fetchDevices();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to link');
      }
    } catch (e) {
      setError('Failed to link image');
    }
  };

  const handleUnlink = async (name: string) => {
    try {
      const res = await apiFetch(`/api/v1/boot/iscsi/images/${name}/unlink`, { method: 'POST' });
      if (res.ok) {
        setSuccess(`Image "${name}" unlinked`);
        await fetchImages();
        await fetchDevices();
      } else {
        const data = await res.json();
        setError(data.detail || 'Failed to unlink');
      }
    } catch (e) {
      setError('Failed to unlink image');
    }
  };

  const sizeOptions = [4, 32, 64, 128, 256];

  return (
    <div className="iscsi-management">
      {/* Status messages */}
      {error && (
        <div style={{ background: '#dc354520', border: '1px solid #dc3545', color: '#ff6b6b', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px' }}>
          {error}
        </div>
      )}
      {success && (
        <div style={{ background: '#28a74520', border: '1px solid #28a745', color: '#51cf66', padding: '12px 16px', borderRadius: '8px', marginBottom: '16px' }}>
          {success}
        </div>
      )}

      {/* Create iSCSI Image */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-title">
          💿 Create iSCSI Image
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '14px' }}>
          Create a new iSCSI disk image that can be linked to a device for network boot installation.
        </p>
        <form onSubmit={handleCreate} style={{ display: 'flex', gap: '12px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ flex: 1, minWidth: '200px', margin: 0 }}>
            <label>Image Name</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g., win11-workstation"
              required
              pattern="[a-zA-Z0-9_-]+"
              title="Only letters, numbers, hyphens and underscores"
            />
          </div>
          <div className="form-group" style={{ width: '160px', margin: 0 }}>
            <label>Size</label>
            <select value={newSize} onChange={(e) => setNewSize(Number(e.target.value))}>
              {sizeOptions.map(s => (
                <option key={s} value={s}>{s} GB</option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn-success" disabled={creating} style={{ height: '38px' }}>
            {creating ? 'Creating...' : '+ Create Image'}
          </button>
        </form>
      </div>

      {/* Images List */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: '16px' }}>
          📀 iSCSI Images
          <span style={{ fontSize: '14px', fontWeight: 'normal', color: 'var(--text-secondary)', marginLeft: '12px' }}>
            {images.length} image{images.length !== 1 ? 's' : ''}
          </span>
        </div>

        {loading ? (
          <div className="loading"><div className="spinner"></div></div>
        ) : images.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No iSCSI images</h3>
            <p>Create your first iSCSI image to get started with network boot</p>
          </div>
        ) : (
          <div className="list-container">
            {images.map((img) => (
              <div key={img.id} className="list-item" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>
                      {img.name}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '12px', marginTop: '4px' }}>
                      Size: {img.size_gb} GB
                      {img.actual_size_gb !== undefined && ` (actual: ${img.actual_size_gb} GB)`}
                      {img.target_name && ` • Target: ${img.target_name}`}
                    </div>
                    <div style={{ marginTop: '8px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      {img.assigned_to ? (
                        <span className="badge badge-success">
                          ✓ Linked: {img.assigned_to}
                        </span>
                      ) : (
                        <span className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                          Available
                        </span>
                      )}
                      {img.status === 'unregistered' && (
                        <span className="badge" style={{ background: '#ffc10720', color: '#ffc107' }}>
                          Unregistered
                        </span>
                      )}
                      {img.copied_from && (
                        <span className="badge" style={{ background: 'var(--bg-tertiary)', color: 'var(--text-secondary)' }}>
                          Copied from: {img.copied_from}
                        </span>
                      )}
                      {!img.file_exists && (
                        <span className="badge" style={{ background: '#dc354520', color: '#ff6b6b' }}>
                          File missing!
                        </span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                    <button className="btn-primary btn-small" onClick={() => { setLinking(img.id); setLinkMac(''); }}>
                      Link
                    </button>
                    <button className="btn-outline btn-small" onClick={() => { setCopying(img.id); setCopyName(`${img.id}-copy`); }}>
                      Copy
                    </button>
                    {img.assigned_to && (
                      <button className="btn-outline btn-small" onClick={() => handleUnlink(img.id)}>
                        Unlink
                      </button>
                    )}
                    <button className="btn-danger btn-small" onClick={() => handleDelete(img.id)}>
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Copy Modal */}
      {copying && (
        <div className="modal-overlay active">
          <div className="modal">
            <div className="modal-header">Copy iSCSI Image</div>
            <div style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
              Source: <strong>{copying}</strong>
            </div>
            <div className="form-group">
              <label>New Image Name</label>
              <input
                type="text"
                value={copyName}
                onChange={(e) => setCopyName(e.target.value)}
                placeholder="e.g., win11-copy"
                pattern="[a-zA-Z0-9_-]+"
              />
            </div>
            <div className="modal-footer">
              <button className="btn-outline" onClick={() => setCopying(null)}>Cancel</button>
              <button className="btn-primary" onClick={handleCopy} disabled={!copyName.trim()}>Copy Image</button>
            </div>
          </div>
        </div>
      )}

      {/* Link Modal */}
      {linking && (
        <div className="modal-overlay active">
          <div className="modal">
            <div className="modal-header">Link Image to Device</div>
            <div style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
              Image: <strong>{linking}</strong>
            </div>
            <div className="form-group">
              <label>Select Device (MAC)</label>
              <select value={linkMac} onChange={(e) => setLinkMac(e.target.value)}>
                <option value="">Choose a device...</option>
                {devices.map((d) => (
                  <option key={d.mac} value={d.mac}>
                    {d.name} ({d.mac})
                  </option>
                ))}
              </select>
            </div>
            {linkMac && (
              <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                Device: {devices.find(d => d.mac === linkMac)?.name}<br/>
                Type: {devices.find(d => d.mac === linkMac)?.device_type}
              </div>
            )}
            <div className="modal-footer">
              <button className="btn-outline" onClick={() => setLinking(null)}>Cancel</button>
              <button className="btn-primary" onClick={handleLink} disabled={!linkMac}>Link Image</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
