import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

interface LoginPageProps {
  onNeedSetup?: () => void;
}

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

export const LoginPage: React.FC<LoginPageProps> = ({ onNeedSetup: _onNeedSetup }) => {
  const { login, continueAsGuest } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
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

        <div className="auth-divider">or</div>

        <button
          type="button"
          className="btn-secondary auth-guest"
          onClick={continueAsGuest}
          disabled={loading}
        >
          Continue as Guest (read-only)
        </button>

        <p className="auth-hint">
          Guests can view the dashboard and upload OS installers.
        </p>
      </div>
    </div>
  );
};
