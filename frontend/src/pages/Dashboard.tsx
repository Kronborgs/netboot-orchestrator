import React, { useState, useEffect } from 'react';
import { DeviceList } from '../components/DeviceList';
import { apiFetch } from '../api/client';

interface Stats {
  activeDevices: number;
  totalDevices: number;
  iscsiImages: number;
  linkedImages: number;
  osInstallers: number;
  storageUsed: number;
  iscsiStorageUsed: number;
  osStorageUsed: number;
}

interface DashboardProps {
  onOpenDevices?: () => void;
  onOpenIscsi?: () => void;
  onOpenInstallers?: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({
  onOpenDevices,
  onOpenIscsi,
  onOpenInstallers
}) => {
  const [stats, setStats] = useState<Stats>({
    activeDevices: 0,
    totalDevices: 0,
    iscsiImages: 0,
    linkedImages: 0,
    osInstallers: 0,
    storageUsed: 0,
    iscsiStorageUsed: 0,
    osStorageUsed: 0
  });
  const [loading, setLoading] = useState(true);
  const [showStorageMenu, setShowStorageMenu] = useState(false);

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
        apiFetch(`/api/v1/devices`),
        apiFetch(`/api/v1/boot/iscsi/images`),
        apiFetch(`/api/v1/os-installers/files`),
        apiFetch(`/api/v1/storage/info`)
      ]);

      let devices = [], images = [], osFiles = {}, storage = {};
      
      if (devicesRes.ok) devices = await devicesRes.json();
      if (imagesRes.ok) images = await imagesRes.json();
      if (osRes.ok) osFiles = await osRes.json();
      if (storageRes.ok) storage = await storageRes.json();

      const activeDevices = devices.filter((d: any) => d.enabled).length;
      const linkedImages = images.filter((i: any) => i.assigned_to).length;

      setStats({
        activeDevices,
        totalDevices: devices.length,
        iscsiImages: images.length,
        linkedImages,
        osInstallers: (osFiles as any).file_count || 0,
        storageUsed: (storage as any).total?.size_gb || 0,
        iscsiStorageUsed: (storage as any).images?.size_gb || 0,
        osStorageUsed: (storage as any).os_installers?.size_gb || 0
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
        <div className="card dashboard-click-card" style={{ textAlign: 'center', padding: '24px' }} onClick={onOpenDevices}>
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

        <div className="card dashboard-click-card" style={{ textAlign: 'center', padding: '24px' }} onClick={onOpenIscsi}>
          <div style={{ fontSize: '32px', marginBottom: '8px' }}>💿</div>
          <h3 style={{ margin: '8px 0' }}>iSCSI Images</h3>
          <div style={{ 
            fontSize: '36px', 
            fontWeight: 'bold', 
            color: 'var(--accent-orange)',
            marginBottom: '4px'
          }}>
            {loading ? '-' : stats.iscsiImages}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {stats.linkedImages} linked to devices
          </div>
        </div>

        <div className="card dashboard-click-card" style={{ textAlign: 'center', padding: '24px' }} onClick={onOpenInstallers}>
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

        <div
          className="card dashboard-click-card"
          style={{ textAlign: 'center', padding: '24px' }}
          onClick={() => setShowStorageMenu((prev) => !prev)}
        >
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

      {showStorageMenu && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <h3 style={{ marginBottom: '14px' }}>💾 Storage Under Menu</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: '12px' }}>
            <div className="list-item" style={{ borderBottom: 'none', borderRadius: '8px' }}>
              <div>
                <div style={{ fontWeight: 600 }}>💿 iSCSI Images</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{stats.iscsiStorageUsed.toFixed(1)} GB</div>
              </div>
              <button className="btn-primary btn-small" onClick={(e) => { e.stopPropagation(); onOpenIscsi?.(); }}>
                Open
              </button>
            </div>
            <div className="list-item" style={{ borderBottom: 'none', borderRadius: '8px' }}>
              <div>
                <div style={{ fontWeight: 600 }}>📦 OS Installers</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{stats.osStorageUsed.toFixed(1)} GB</div>
              </div>
              <button className="btn-primary btn-small" onClick={(e) => { e.stopPropagation(); onOpenInstallers?.(); }}>
                Open
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <h2 style={{ marginBottom: '16px' }}>📋 Recent Devices</h2>
        <DeviceList />
      </div>
    </div>
  );
};

