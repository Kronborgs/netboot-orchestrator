import React from 'react';
import { ImageManagement } from '../components/ImageManagement';
import { OsInstallerList } from '../components/OsInstallerList';
import { UnknownDeviceWizard } from '../components/UnknownDeviceWizard';
import { DeviceList } from '../components/DeviceList';

export const Inventory: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<'devices' | 'images' | 'installers' | 'wizard'>('devices');

  return (
    <div className="inventory">
      <h1>📦 Inventory & Management</h1>
      <p style={{ color: 'var(--text-secondary)' }}>Manage devices, images, and OS installers for network booting</p>

      <div className="tabs">
        <button
          className={`tab-button ${activeTab === 'devices' ? 'active' : ''}`}
          onClick={() => setActiveTab('devices')}
        >
          🖥️ Devices
        </button>
        <button
          className={`tab-button ${activeTab === 'images' ? 'active' : ''}`}
          onClick={() => setActiveTab('images')}
        >
          💿 Images
        </button>
        <button
          className={`tab-button ${activeTab === 'installers' ? 'active' : ''}`}
          onClick={() => setActiveTab('installers')}
        >
          🖱️ OS Installers
        </button>
        <button
          className={`tab-button ${activeTab === 'wizard' ? 'active' : ''}`}
          onClick={() => setActiveTab('wizard')}
        >
          🧙 Device Wizard
        </button>
      </div>

      <div className="tab-content active" style={{ marginTop: '24px' }}>
        {activeTab === 'devices' && <DeviceList />}
        {activeTab === 'images' && <ImageManagement />}
        {activeTab === 'installers' && <OsInstallerList />}
        {activeTab === 'wizard' && <UnknownDeviceWizard />}
      </div>
    </div>
  );
};

