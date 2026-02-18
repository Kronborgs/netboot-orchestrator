import React, { useState, useEffect } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Inventory } from './pages/Inventory';
import { SetupGuide } from './pages/SetupGuide';
import './styles/index.css';

type Page = 'dashboard' | 'inventory' | 'setup';

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

function App() {
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [version, setVersion] = useState<string>('');

  useEffect(() => {
    // Dark mode is always on (default)
    document.documentElement.style.colorScheme = 'dark';
  }, [isDarkMode]);

  useEffect(() => {
    // Fetch version from API - use same host as frontend
    const apiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/v1/version`;
    fetch(apiUrl)
      .then(res => res.json())
      .then(data => setVersion(data.version || ''))
      .catch(() => setVersion('2026-02-18-V1'));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <img
              src={LOGO_URL}
              alt="Netboot Orchestrator"
              style={{ height: '40px', width: 'auto', maxWidth: '180px', objectFit: 'contain' }}
            />
            <div>
              <h1 style={{ margin: '0 0 2px 0', fontSize: '24px' }}>Netboot Orchestrator</h1>
              <div style={{ fontSize: '12px', opacity: 0.9 }}>Network Boot Manager — Designed by Kenneth Kronborg AI Team</div>
            </div>
          </div>

          <nav className="header nav" style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              className={currentPage === 'dashboard' ? 'active' : ''}
              onClick={() => setCurrentPage('dashboard')}
              style={{
                background: currentPage === 'dashboard' ? 'rgba(255,255,255,0.3)' : 'transparent',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                padding: '8px 16px',
                borderRadius: '6px',
                transition: 'all 0.2s',
                fontSize: '14px'
              }}
            >
              📊 Dashboard
            </button>
            <button
              className={currentPage === 'inventory' ? 'active' : ''}
              onClick={() => setCurrentPage('inventory')}
              style={{
                background: currentPage === 'inventory' ? 'rgba(255,255,255,0.3)' : 'transparent',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                padding: '8px 16px',
                borderRadius: '6px',
                transition: 'all 0.2s',
                fontSize: '14px'
              }}
            >
              📦 Inventory
            </button>
            <button
              className={currentPage === 'setup' ? 'active' : ''}
              onClick={() => setCurrentPage('setup')}
              style={{
                background: currentPage === 'setup' ? 'rgba(255,255,255,0.3)' : 'transparent',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                padding: '8px 16px',
                borderRadius: '6px',
                transition: 'all 0.2s',
                fontSize: '14px'
              }}
            >
              ⚙️ Setup Guide
            </button>
          </nav>
        </div>
      </header>

      <main className="main-content">
        {currentPage === 'dashboard' && <Dashboard />}
        {currentPage === 'inventory' && <Inventory />}
        {currentPage === 'setup' && <SetupGuide />}
      </main>

      <footer style={{
        padding: '24px',
        background: 'var(--bg-secondary)',
        textAlign: 'center',
        borderTop: '1px solid var(--border-color)',
        marginTop: '40px',
        color: 'var(--text-secondary)',
        fontSize: '12px'
      }}>
        <div style={{ marginBottom: '8px' }}>Netboot Orchestrator {version && `v${version}`}</div>
        <div style={{ marginBottom: '4px' }}>Network boot management for Raspberry Pi, x86, and x64 systems</div>
        <div style={{ opacity: 0.7 }}>Designed by Kenneth Kronborg AI Team</div>
      </footer>
    </div>
  );
}

export default App;

