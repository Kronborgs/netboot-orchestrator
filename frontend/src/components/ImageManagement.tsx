import React, { useState, useEffect } from 'react';

interface Image {
  id: string;
  name: string;
  size_gb: number;
  device_type: string;
  assigned_to?: string;
  created_at: string;
}

interface Device {
  mac: string;
  name: string;
  device_type: string;
}

export const ImageManagement: React.FC = () => {
  const [images, setImages] = useState<Image[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    size_gb: 0,
    device_type: 'raspi'
  });
  const [assignImage, setAssignImage] = useState<{ imageId: string; mac: string } | null>(null);

  useEffect(() => {
    fetchImages();
    fetchDevices();
  }, []);

  const fetchImages = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/v1/images`);
      if (res.ok) {
        setImages(await res.json());
      }
    } catch (error) {
      console.error('Failed to fetch images:', error);
    }
    setLoading(false);
  };

  const fetchDevices = async () => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/devices`);
      if (res.ok) {
        setDevices(await res.json());
      }
    } catch (error) {
      console.error('Failed to fetch devices:', error);
    }
  };

  const handleCreateImage = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`http://localhost:8000/api/v1/images`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...formData,
          created_at: new Date().toISOString()
        })
      });
      if (res.ok) {
        setFormData({ id: '', name: '', size_gb: 0, device_type: 'raspi' });
        setShowForm(false);
        fetchImages();
      }
    } catch (error) {
      console.error('Failed to create image:', error);
    }
  };

  const handleAssignImage = async () => {
    if (!assignImage) return;
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/images/${assignImage.imageId}/assign?mac=${assignImage.mac}`,
        { method: 'PUT' }
      );
      if (res.ok) {
        setAssignImage(null);
        fetchImages();
        fetchDevices();
      }
    } catch (error) {
      console.error('Failed to assign image:', error);
    }
  };

  const handleUnassignImage = async (imageId: string) => {
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/images/${imageId}/unassign`,
        { method: 'PUT' }
      );
      if (res.ok) {
        fetchImages();
        fetchDevices();
      }
    } catch (error) {
      console.error('Failed to unassign image:', error);
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    if (!confirm('Are you sure you want to delete this image?')) return;
    try {
      const res = await fetch(`http://localhost:8000/api/v1/images/${imageId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchImages();
      }
    } catch (error) {
      console.error('Failed to delete image:', error);
    }
  };

  return (
    <div className="image-management">
      <div className="card">
        <div className="card-title">
          📀 Create, manage, and assign iSCSI disk images to devices
        </div>

        <button 
          className="btn-primary mb-3"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : '+ Create New Image'}
        </button>

        {showForm && (
          <form onSubmit={handleCreateImage} className="card mb-3" style={{ background: 'var(--bg-tertiary)' }}>
            <h3>Create New iSCSI Image</h3>
            
            <div className="form-group">
              <label>Image ID</label>
              <input
                type="text"
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                placeholder="e.g., ubuntu-22-raspi"
                required
              />
            </div>

            <div className="form-group">
              <label>Image Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Ubuntu 22.04 LTS"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Size (GB)</label>
                <input
                  type="number"
                  value={formData.size_gb}
                  onChange={(e) => setFormData({ ...formData, size_gb: parseFloat(e.target.value) })}
                  placeholder="0"
                  step="0.1"
                  required
                />
              </div>

              <div className="form-group">
                <label>Device Type</label>
                <select
                  value={formData.device_type}
                  onChange={(e) => setFormData({ ...formData, device_type: e.target.value })}
                  required
                >
                  <option value="raspi">Raspberry Pi</option>
                  <option value="x86">x86</option>
                  <option value="x64">x64</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '8px' }}>
              <button type="submit" className="btn-success">
                Create Image
              </button>
            </div>
          </form>
        )}
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      ) : images.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No images yet</h3>
            <p>Create your first iSCSI image to get started</p>
          </div>
        </div>
      ) : (
        <div className="list-container">
          {images.map((image) => (
            <div key={image.id} className="list-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '12px' }}>
              <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)' }}>
                    {image.name}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                    ID: {image.id} • Size: {image.size_gb} GB • Type: {image.device_type}
                  </div>
                  {image.assigned_to && (
                    <div style={{ marginTop: '8px' }}>
                      <span className="badge badge-success">
                        ✓ Assigned to {image.assigned_to}
                      </span>
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="btn-primary btn-small"
                    onClick={() => setAssignImage({ imageId: image.id, mac: '' })}
                  >
                    Assign
                  </button>
                  {image.assigned_to && (
                    <button
                      className="btn-outline btn-small"
                      onClick={() => handleUnassignImage(image.id)}
                    >
                      Unassign
                    </button>
                  )}
                  <button
                    className="btn-danger btn-small"
                    onClick={() => handleDeleteImage(image.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {assignImage && (
        <div className="modal-overlay active">
          <div className="modal">
            <div className="modal-header">Assign Image to Device</div>
            <div style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
              Image: <strong>{images.find(img => img.id === assignImage.imageId)?.name}</strong>
            </div>

            <div className="form-group">
              <label>Select Device (MAC)</label>
              <select
                value={assignImage.mac}
                onChange={(e) => setAssignImage({ ...assignImage, mac: e.target.value })}
              >
                <option value="">Choose a device...</option>
                {devices.map((device) => (
                  <option key={device.mac} value={device.mac}>
                    {device.name} ({device.mac})
                  </option>
                ))}
              </select>
            </div>

            {assignImage.mac && devices.find(d => d.mac === assignImage.mac) && (
              <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '6px', marginBottom: '16px' }}>
                <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                  <div>Device: {devices.find(d => d.mac === assignImage.mac)?.name}</div>
                  <div>Type: {devices.find(d => d.mac === assignImage.mac)?.device_type}</div>
                </div>
              </div>
            )}

            <div className="modal-footer">
              <button
                className="btn-outline"
                onClick={() => setAssignImage(null)}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleAssignImage}
                disabled={!assignImage.mac}
              >
                Assign Image
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

