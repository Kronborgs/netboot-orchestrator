import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getApiUrl } from '../api/client';

interface LoginPageProps {
  onNeedSetup?: () => void;
  onClose?: () => void;
}

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

export const LoginPage: React.FC<LoginPageProps> = ({ onNeedSetup: _onNeedSetup, onClose }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [version, setVersion] = useState('');

  useEffect(() => {
    fetch(getApiUrl('/api/v1/version'))
      .then(r => r.json())
      .then(d => setVersion(d.version || ''))
      .catch(() => setVersion('2026-03-06-V215'));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      onClose?.();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const card = (
    <div className="auth-card">
      {onClose && (
        <button className="modal-close-btn" onClick={onClose} title="Close">✕</button>
      )}
      <div className="auth-header">
        <img src={LOGO_URL} alt="Netboot Orchestrator" className="auth-logo" />
        <h1>Netboot Orchestrator</h1>
        <p className="auth-subtitle">Sign in to manage your network boot infrastructure</p>
      </div>

      <form onSubmit={handleSubmit} className="auth-form">
        {error && <div className="auth-error">{error}</div>}

        <div className="auth-field">
          <label htmlFor="username">Username</label>
          <input
            id="username"
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
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="••••••••"
            disabled={loading}
            required
          />
        </div>

        <button type="submit" className="btn-primary auth-submit" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>

      {onClose && (
        <>
          <div className="auth-divider">or</div>
          <button
            type="button"
            className="btn-secondary auth-guest"
            onClick={onClose}
            disabled={loading}
          >
            Continue as Guest (read-only)
          </button>
          <p className="auth-hint">Guests can view the dashboard and upload OS installers.</p>
        </>
      )}
      <p className="auth-version">v{version || '2026-03-06-V215'}</p>
    </div>
  );

  if (onClose) {
    return (
      <div
        className="login-modal-overlay"
        onClick={e => { if (e.target === e.currentTarget) onClose(); }}
      >
        {card}
      </div>
    );
  }

  return <div className="auth-page">{card}</div>;
};
