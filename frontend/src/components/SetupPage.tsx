import React, { useState, useEffect } from 'react';
import { apiFetch, getApiUrl } from '../api/client';
import { useAuth } from '../contexts/AuthContext';

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

export const SetupPage: React.FC<{ onCreated?: () => void }> = ({ onCreated }) => {
  const { continueAsGuest } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [version, setVersion] = useState('');

  useEffect(() => {
    fetch(getApiUrl('/api/v1/version'))
      .then(r => r.json())
      .then(d => setVersion(d.version || ''))
      .catch(() => setVersion('2026-03-13-V230'));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (username.trim().length < 3) {
      setError('Username must be at least 3 characters');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/auth/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim(), password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Setup failed');
        return;
      }
      // Account created — tell AppShell admin now exists, it will auto-guest
      if (onCreated) {
        onCreated();
      } else {
        continueAsGuest();
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Setup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <img src={LOGO_URL} alt="Netboot Orchestrator" className="auth-logo" />
          <h1>Welcome to Netboot Orchestrator</h1>
          <p className="auth-subtitle">Create your admin account to get started</p>
        </div>

        <div className="auth-banner">
          🔒 <strong>First-run setup</strong> — this screen only appears once.
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          {error && <div className="auth-error">{error}</div>}

          <div className="auth-field">
            <label htmlFor="su-username">Admin Username</label>
            <input
              id="su-username"
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="admin"
              autoFocus
              disabled={loading}
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="su-password">Password</label>
            <input
              id="su-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              disabled={loading}
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="su-confirm">Confirm Password</label>
            <input
              id="su-confirm"
              type="password"
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              placeholder="Repeat password"
              disabled={loading}
              required
            />
          </div>

          <button type="submit" className="btn-primary auth-submit" disabled={loading}>
            {loading ? 'Creating account…' : 'Create Admin Account'}
          </button>
        </form>
        <p className="auth-version">v{version || '2026-03-13-V230'}</p>
      </div>
    </div>
  );
};
