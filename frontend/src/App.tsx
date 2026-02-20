import React, { useState, useEffect } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Inventory } from './pages/Inventory';
import { SetupGuide } from './pages/SetupGuide';
import './styles/index.css';

type Page = 'dashboard' | 'inventory' | 'setup';

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    // Dark mode is always on (default)
    document.documentElement.style.colorScheme = 'dark';
  }, []);

  useEffect(() => {
    // Fetch version from API - use same host as frontend
    const apiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/v1/version`;
    fetch(apiUrl)
      .then(res => res.json())
      .then(data => setVersion(data.version || ''))
      .catch(() => setVersion('2026-02-18-V1'));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <img src={LOGO_URL} alt="Netboot Orchestrator" className="sidebar-logo" />
          <div className="sidebar-brand-text">
            <div className="brand-title">Netboot Orchestrator</div>
            <div className="brand-subtitle">Network Boot Manager</div>
          </div>
        </div>

        <nav className="side-nav">
          <button
            className={`side-nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
            onClick={() => setCurrentPage('dashboard')}
          >
            📊 Dashboard
          </button>
          <button
            className={`side-nav-btn ${currentPage === 'inventory' ? 'active' : ''}`}
            onClick={() => setCurrentPage('inventory')}
          >
            📦 Inventory
          </button>
          <button
            className={`side-nav-btn ${currentPage === 'setup' ? 'active' : ''}`}
            onClick={() => setCurrentPage('setup')}
          >
            ⚙️ Setup Guide
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-version">{version ? `v${version}` : 'version loading...'}</div>
          <div className="sidebar-credit">Designed by Kenneth Kronborg AI Team</div>
        </div>
      </aside>

      <div className="content-area">
        <header className="topbar">
          <div className="topbar-path">{currentPage === 'dashboard' ? 'Dashboard' : currentPage === 'inventory' ? 'Inventory' : 'Setup Guide'}</div>
          <div className="topbar-right">
            <input className="topbar-search" placeholder="Søg her..." />
            <span className="topbar-user">Sign in</span>
          </div>
        </header>

        <main className="main-content">
          {currentPage === 'dashboard' && <Dashboard />}
          {currentPage === 'inventory' && <Inventory />}
          {currentPage === 'setup' && <SetupGuide />}
        </main>

        <footer className="app-footer">
          <div>Netboot Orchestrator {version && `v${version}`}</div>
          <div>Network boot management for Raspberry Pi, x86, and x64 systems</div>
        </footer>
      </div>
    </div>
  );
}

export default App;

