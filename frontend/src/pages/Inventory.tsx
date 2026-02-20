import React from 'react';
import { ImageManagement } from '../components/ImageManagement';
import { IscsiManagement } from '../components/IscsiManagement';
import { OsInstallerList } from '../components/OsInstallerList';
import { UnknownDeviceWizard } from '../components/UnknownDeviceWizard';
import { DeviceList } from '../components/DeviceList';
import { BootLogs } from '../components/BootLogs';

type InventoryTab = 'devices' | 'iscsi' | 'installers' | 'logs' | 'wizard';

interface InventoryProps {
  initialTab?: InventoryTab;
}

export const Inventory: React.FC<InventoryProps> = ({ initialTab = 'devices' }) => {
  const [activeTab, setActiveTab] = React.useState<InventoryTab>(initialTab);

  React.useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  return (
    <div className="inventory">
      <h1>📦 Inventory & Management</h1>
      <p style={{ color: 'var(--text-secondary)' }}>Manage devices, iSCSI images, OS installers, and boot activity</p>

      <div className="tabs">
        <button
          className={`tab-button ${activeTab === 'devices' ? 'active' : ''}`}
          onClick={() => setActiveTab('devices')}
        >
          🖥️ Devices
        </button>
        <button
          className={`tab-button ${activeTab === 'iscsi' ? 'active' : ''}`}
          onClick={() => setActiveTab('iscsi')}
        >
          💿 iSCSI Images
        </button>
        <button
          className={`tab-button ${activeTab === 'installers' ? 'active' : ''}`}
          onClick={() => setActiveTab('installers')}
        >
          🖱️ OS Installers
        </button>
        <button
          className={`tab-button ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          📡 Boot Logs
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
        {activeTab === 'iscsi' && <IscsiManagement />}
        {activeTab === 'installers' && <OsInstallerList />}
        {activeTab === 'logs' && <BootLogs />}
        {activeTab === 'wizard' && <UnknownDeviceWizard />}
      </div>
    </div>
  );
};

