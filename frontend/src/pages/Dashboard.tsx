import React from 'react';
import { DeviceList } from '../components/DeviceList';

export const Dashboard: React.FC = () => {
  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      <div className="stats">
        <div className="stat-card">
          <h3>Active Devices</h3>
          <p>0</p>
        </div>
        <div className="stat-card">
          <h3>iSCSI Images</h3>
          <p>0</p>
        </div>
        <div className="stat-card">
          <h3>OS Installers</h3>
          <p>0</p>
        </div>
      </div>
      <DeviceList />
    </div>
  );
};
