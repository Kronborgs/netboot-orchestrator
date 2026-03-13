import React, { useState, useEffect } from 'react';
import { Dashboard } from './pages/Dashboard';
import { Inventory } from './pages/Inventory';
import { SetupGuide } from './pages/SetupGuide';
import { Administration } from './pages/Administration';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginPage } from './components/LoginPage';
import { SetupPage } from './components/SetupPage';
import { ResetPasswordPage } from './components/ResetPasswordPage';
import { getApiUrl } from './api/client';
import './styles/index.css';

type Page = 'dashboard' | 'inventory' | 'setup' | 'administration';
type InventoryTab = 'devices' | 'iscsi' | 'installers' | 'logs' | 'wizard';

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

// ---------------------------------------------------------------------------
// Inner app — rendered only when auth state is resolved
// ---------------------------------------------------------------------------
function AppShell() {
  const { user, isAdmin, isLoading, logout, continueAsGuest } = useAuth();
  const [currentPage, setCurrentPage] = useState<Page>('dashboard');
  const [inventoryTab, setInventoryTab] = useState<InventoryTab>('devices');
  const [version, setVersion] = useState<string>('');
  const [hasAdmin, setHasAdmin] = useState<boolean | null>(null);
  const [setupChecked, setSetupChecked] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);

  const openInventoryTab = (tab: InventoryTab) => {
    setInventoryTab(tab);
    setCurrentPage('inventory');
  };

  useEffect(() => {
    document.documentElement.style.colorScheme = 'dark';
  }, []);

  useEffect(() => {
    const apiUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/v1/version`;
    fetch(apiUrl)
      .then(res => res.json())
      .then(data => setVersion(data.version || ''))
      .catch(() => setVersion('2026-03-13-V236'));
  }, []);

  // Check if any admin exists (first-run detection)
  useEffect(() => {
    fetch(getApiUrl('/api/v1/auth/setup-status'))
      .then(res => res.json())
      .then(data => setHasAdmin(Boolean(data.has_admin)))
      .catch(() => setHasAdmin(true))   // assume admin exists if API is unreachable
      .finally(() => setSetupChecked(true));
  }, []);

  // Auto-continue as guest once everything is loaded and admin exists but user is not set
  useEffect(() => {
    if (!isLoading && setupChecked && hasAdmin && !user) {
      continueAsGuest();
    }
  }, [isLoading, setupChecked, hasAdmin, user, continueAsGuest]);

  // Wait until both auth rehydration and setup-status are done
  if (isLoading || !setupChecked) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: 'center', padding: '2rem' }}>
          <p style={{ color: 'var(--text-muted)' }}>Loading…</p>
        </div>
      </div>
    );
  }

  // First-run: no admin exists yet
  if (!hasAdmin) {
    return <SetupPage onCreated={() => setHasAdmin(true)} />;
  }

  // Still waiting for auto-guest to kick in
  if (!user) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: 'center', padding: '2rem' }}>
          <p style={{ color: 'var(--text-muted)' }}>Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="sidebar-brand" onClick={() => setCurrentPage('dashboard')}>
          <img src={LOGO_URL} alt="Netboot Orchestrator" className="sidebar-logo" />
          <div className="sidebar-brand-text">
            <div className="brand-title">Netboot Orchestrator</div>
            <div className="brand-subtitle">Network Boot Manager</div>
          </div>
        </button>

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
          {isAdmin && (
            <button
              className={`side-nav-btn side-nav-btn--admin ${currentPage === 'administration' ? 'active' : ''}`}
              onClick={() => setCurrentPage('administration')}
            >
              🔐 Administration
            </button>
          )}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-version">{version ? `v${version}` : 'version loading...'}</div>
          <div className="sidebar-credit">Designed by Kenneth Kronborg AI Team</div>
        </div>
      </aside>

      <div className="content-area">
        <header className="topbar">
          <button className="topbar-path" onClick={() => setCurrentPage('dashboard')}>Dashboard</button>
          <div className="topbar-right">
            <input className="topbar-search" placeholder="Søg her..." />
            {isAdmin ? (
              <span className="topbar-user topbar-user--admin" title={`Signed in as ${user.role === 'super_user' ? 'super user' : 'admin'}`}>
                👤 {user.username}
                <button className="topbar-signout" onClick={logout} title="Sign out">Sign out</button>
              </span>
            ) : (
              <button
                className="topbar-user topbar-user--guest"
                onClick={() => setShowLoginModal(true)}
                title="Click to sign in"
              >
                Sign in
              </button>
            )}
          </div>
        </header>

        <main className="main-content">
          {currentPage === 'dashboard' && (
            <Dashboard
              onOpenDevices={() => openInventoryTab('devices')}
              onOpenIscsi={() => openInventoryTab('iscsi')}
              onOpenInstallers={() => openInventoryTab('installers')}
            />
          )}
          {currentPage === 'inventory' && (
            <Inventory initialTab={inventoryTab} isAdmin={isAdmin} />
          )}
          {currentPage === 'setup' && <SetupGuide />}
          {currentPage === 'administration' && isAdmin && <Administration />}
        </main>

        <footer className="app-footer">
          <div>Netboot Orchestrator {version && `v${version}`}</div>
          <div>Network boot management for Raspberry Pi, x86, and x64 systems</div>
        </footer>
      </div>

      {showLoginModal && (
        <LoginPage onClose={() => setShowLoginModal(false)} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Root — wraps everything in AuthProvider
// ---------------------------------------------------------------------------
function App() {
  // Detect password reset token in URL before rendering anything else
  const params = new URLSearchParams(window.location.search);
  const resetToken = params.get('token');

  const clearResetToken = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete('token');
    window.history.replaceState({}, '', url.toString());
  };

  if (resetToken) {
    return <ResetPasswordPage token={resetToken} onDone={clearResetToken} />;
  }

  return (
    <AuthProvider>
      <AppShell />
    </AuthProvider>
  );
}

export default App;

