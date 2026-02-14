import React, { useState, useEffect } from 'react';
import api from '../api';
import { Device } from '../types';

export const DeviceList: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDevices();
  }, []);

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/v1/devices');
      setDevices(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch devices');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const deleteDevice = async (mac: string) => {
    try {
      await api.delete(`/api/v1/devices/${mac}`);
      setDevices(devices.filter(d => d.mac !== mac));
    } catch (err) {
      setError('Failed to delete device');
      console.error(err);
    }
  };

  if (loading) return <div>Loading devices...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="device-list">
      <h2>Registered Devices</h2>
      {devices.length === 0 ? (
        <p>No devices registered yet</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>MAC Address</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Image</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr key={device.mac}>
                <td>{device.mac}</td>
                <td>{device.name}</td>
                <td>{device.device_type}</td>
                <td>{device.enabled ? 'Enabled' : 'Disabled'}</td>
                <td>{device.image_id || '—'}</td>
                <td>
                  <button onClick={() => deleteDevice(device.mac)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
