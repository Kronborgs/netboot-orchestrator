import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getApiUrl, apiFetch } from '../api/client';

interface LoginPageProps {
  onNeedSetup?: () => void;
  onClose?: () => void;
}

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

// ---------------------------------------------------------------------------
// Forgot-password sub-view
// ---------------------------------------------------------------------------
const ForgotPasswordView: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const [identifier, setIdentifier] = useState('');
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg(null);
    setLoading(true);
    try {
      const base_url = window.location.origin + window.location.pathname;
      const res = await apiFetch('/api/v1/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier: identifier.trim(), base_url }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg({ type: 'err', text: data.detail || 'Request failed' });
      } else {
        setMsg({ type: 'ok', text: data.message || 'Reset link sent.' });
      }
    } catch {
      setMsg({ type: 'err', text: 'Network error — please try again' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <h2 style={{ margin: '0 0 6px', fontSize: '1.1rem' }}>Forgot Password</h2>
      <p className="auth-hint" style={{ margin: '0 0 1rem' }}>
        Enter your <strong>username</strong> or <strong>email address</strong>.<br />
        A reset link will be sent to your registered email.
      </p>

      {msg && (
        <div className={msg.type === 'ok' ? 'auth-ok' : 'auth-error'} style={{ marginBottom: '1rem' }}>
          {msg.text}
        </div>
      )}

      {!msg?.type || msg.type === 'err' ? (
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label htmlFor="fp-identifier">Username or Email</label>
            <input
              id="fp-identifier"
              type="text"
              value={identifier}
              onChange={e => setIdentifier(e.target.value)}
              placeholder="admin or user@example.com"
              autoFocus
              required
              disabled={loading}
            />
          </div>
          <button type="submit" className="btn-primary auth-submit" disabled={loading}>
            {loading ? 'Sending…' : 'Send Reset Link'}
          </button>
        </form>
      ) : null}

      <button type="button" className="auth-back-link" onClick={onBack}>
        ← Back to Sign In
      </button>
    </>
  );
};

// ---------------------------------------------------------------------------
// Main login page / modal
// ---------------------------------------------------------------------------
export const LoginPage: React.FC<LoginPageProps> = ({ onNeedSetup: _onNeedSetup, onClose }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [version, setVersion] = useState('');
  const [showForgot, setShowForgot] = useState(false);

  useEffect(() => {
    fetch(getApiUrl('/api/v1/version'))
      .then(r => r.json())
      .then(d => setVersion(d.version || ''))
      .catch(() => setVersion('2026-03-12-V226'));
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

      {showForgot ? (
        <ForgotPasswordView onBack={() => setShowForgot(false)} />
      ) : (
        <>
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

          <div style={{ textAlign: 'center', marginTop: '10px' }}>
            <button type="button" className="auth-back-link" onClick={() => setShowForgot(true)}>
              Forgot password?
            </button>
          </div>

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
        </>
      )}
      <p className="auth-version">v{version || '2026-03-12-V226'}</p>
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
