import React, { useState, useEffect } from 'react';
import { apiFetch } from '../api/client';

interface Device {
  mac: string;
  device_type: string;
  name: string;
  enabled: boolean;
  image_id?: string;
  kernel_set: string;
}

export const DeviceList: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    mac: '',
    device_type: 'raspi',
    name: '',
    enabled: true
  });

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const response = await apiFetch(`/api/v1/devices`);
      if (response.ok) {
        setDevices(await response.json());
        setError(null);
      }
    } catch (err) {
      setError('Failed to fetch devices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiFetch(`/api/v1/devices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setFormData({ mac: '', device_type: 'raspi', name: '', enabled: true });
        setShowForm(false);
        fetchDevices();
      }
    } catch (err) {
      setError('Failed to create device');
      console.error(err);
    }
  };

  const deleteDevice = async (mac: string) => {
    if (!confirm('Are you sure you want to delete this device?')) return;
    try {
      const res = await apiFetch(`/api/v1/devices/${mac}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setDevices(devices.filter(d => d.mac !== mac));
      }
    } catch (err) {
      setError('Failed to delete device');
      console.error(err);
    }
  };

  const toggleDeviceStatus = async (device: Device) => {
    try {
      const res = await apiFetch(`/api/v1/devices/${device.mac}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...device, enabled: !device.enabled })
      });
      if (res.ok) {
        fetchDevices();
      }
    } catch (err) {
      setError('Failed to update device');
      console.error(err);
    }
  };

  if (error) {
    return <div className="card" style={{ color: 'var(--danger-color)' }}>❌ {error}</div>;
  }

  return (
    <div className="device-list">
      <div className="card">
        <button 
          className="btn-primary mb-3"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : '+ Register New Device'}
        </button>

        {showForm && (
          <form onSubmit={handleCreateDevice} className="card mb-3" style={{ background: 'var(--bg-tertiary)' }}>
            <h3>Register New Device</h3>
            
            <div className="form-group">
              <label>MAC Address</label>
              <input
                type="text"
                value={formData.mac}
                onChange={(e) => setFormData({ ...formData, mac: e.target.value })}
                placeholder="e.g., 00:1A:2B:3C:4D:5E"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Device Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., RaspberryPi-01"
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

            <button type="submit" className="btn-success">
              Register Device
            </button>
          </form>
        )}
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      ) : devices.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No devices registered</h3>
            <p>Register your first device to get started</p>
          </div>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>MAC Address</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Image</th>
              <th style={{ width: '150px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr key={device.mac}>
                <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{device.mac}</td>
                <td>{device.name}</td>
                <td>
                  <span style={{ fontSize: '16px' }}>
                    {device.device_type === 'raspi' && '🥧'}
                    {device.device_type === 'x86' && '💻'}
                    {device.device_type === 'x64' && '🖥️'}
                  </span>
                  {' '}{device.device_type.toUpperCase()}
                </td>
                <td>
                  <span className={`badge ${device.enabled ? 'badge-success' : 'badge-danger'}`}>
                    {device.enabled ? '✓ Active' : '⊘ Inactive'}
                  </span>
                </td>
                <td>
                  {device.image_id ? (
                    <span className="badge badge-info">{device.image_id}</span>
                  ) : (
                    <span style={{ color: 'var(--text-secondary)' }}>—</span>
                  )}
                </td>
                <td style={{ display: 'flex', gap: '4px' }}>
                  <button
                    className="btn-small"
                    onClick={() => toggleDeviceStatus(device)}
                    style={{
                      background: device.enabled ? 'var(--accent-orange)' : 'var(--success-color)',
                      color: 'white',
                      border: 'none',
                      padding: '4px 8px',
                      fontSize: '12px'
                    }}
                  >
                    {device.enabled ? 'Disable' : 'Enable'}
                  </button>
                  <button
                    className="btn-danger btn-small"
                    onClick={() => deleteDevice(device.mac)}
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
