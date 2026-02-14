import React from 'react';
import { ImageManagement } from '../components/ImageManagement';
import { OsInstallerList } from '../components/OsInstallerList';
import { UnknownDeviceWizard } from '../components/UnknownDeviceWizard';

export const Inventory: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<'images' | 'installers' | 'wizard'>('images');

  return (
    <div className="inventory">
      <h1>Inventory & Management</h1>
      <div className="tab-navigation">
        <button
          className={activeTab === 'images' ? 'active' : ''}
          onClick={() => setActiveTab('images')}
        >
          Images
        </button>
        <button
          className={activeTab === 'installers' ? 'active' : ''}
          onClick={() => setActiveTab('installers')}
        >
          OS Installers
        </button>
        <button
          className={activeTab === 'wizard' ? 'active' : ''}
          onClick={() => setActiveTab('wizard')}
        >
          Device Wizard
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'images' && <ImageManagement />}
        {activeTab === 'installers' && <OsInstallerList />}
        {activeTab === 'wizard' && <UnknownDeviceWizard />}
      </div>
    </div>
  );
};
