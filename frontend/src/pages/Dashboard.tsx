import React, { useState, useEffect } from 'react';
import { DeviceList } from '../components/DeviceList';

interface Stats {
  activeDevices: number;
  totalDevices: number;
  images: number;
  osInstallers: number;
  storageUsed: number;
}

export const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats>({
    activeDevices: 0,
    totalDevices: 0,
    images: 0,
    osInstallers: 0,
    storageUsed: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      setLoading(true);
      const [
        devicesRes,
        imagesRes,
        osRes,
        storageRes
      ] = await Promise.all([
        fetch(`http://localhost:8000/api/v1/devices`),
        fetch(`http://localhost:8000/api/v1/images`),
        fetch(`http://localhost:8000/api/v1/os-installers/files`),
        fetch(`http://localhost:8000/api/v1/storage/info`)
      ]);

      let devices = [], images = [], osFiles = {}, storage = {};
      
      if (devicesRes.ok) devices = await devicesRes.json();
      if (imagesRes.ok) images = await imagesRes.json();
      if (osRes.ok) osFiles = await osRes.json();
      if (storageRes.ok) storage = await storageRes.json();

      const activeDevices = devices.filter((d: any) => d.enabled).length;

      setStats({
        activeDevices,
        totalDevices: devices.length,
        images: images.length,
        osInstallers: (osFiles as any).file_count || 0,
        storageUsed: (storage as any).total?.size_gb || 0
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dashboard">
      <h1>📊 Dashboard</h1>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>System overview and device management</p>

      <div style={{ 
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '16px',
        marginBottom: '32px'
      }}>
        <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>🟢</div>
          <h3 style={{ margin: '8px 0' }}>Active Devices</h3>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: 'bold', 
            color: 'var(--primary-blue)',
            marginBottom: '4px'
          }}>
            {loading ? '-' : stats.activeDevices}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            of {stats.totalDevices} total
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>💿</div>
          <h3 style={{ margin: '8px 0' }}>iSCSI Images</h3>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: 'bold', 
            color: 'var(--accent-orange)',
            marginBottom: '4px'
          }}>
            {loading ? '-' : stats.images}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Ready to use
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>📦</div>
          <h3 style={{ margin: '8px 0' }}>OS Installers</h3>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: 'bold', 
            color: 'var(--success-color)',
            marginBottom: '4px'
          }}>
            {loading ? '-' : stats.osInstallers}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Available
          </div>
        </div>

        <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>💾</div>
          <h3 style={{ margin: '8px 0' }}>Storage Used</h3>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: 'bold', 
            color: 'var(--warning-color)',
            marginBottom: '4px'
          }}>
            {loading ? '-' : stats.storageUsed.toFixed(1)}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            GB
          </div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginBottom: '16px' }}>📋 Recent Devices</h2>
        <DeviceList />
      </div>
    </div>
  );
};

