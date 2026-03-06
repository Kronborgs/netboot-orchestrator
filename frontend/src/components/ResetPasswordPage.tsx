import React, { useState } from 'react';
import { apiFetch } from '../api/client';

const LOGO_URL = 'https://raw.githubusercontent.com/Kronborgs/netboot-orchestrator/main/docs/logo.png';

interface Props {
  token: string;
  onDone: () => void;
}

export const ResetPasswordPage: React.FC<Props> = ({ token, onDone }) => {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 6) { setError('Password must be at least 6 characters'); return; }
    if (password !== confirm) { setError('Passwords do not match'); return; }
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, password }),
      });
      const data = await res.json();
      if (!res.ok) { setError(data.detail || 'Reset failed'); return; }
      setDone(true);
    } catch {
      setError('Network error — please try again');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <img src={LOGO_URL} alt="Netboot Orchestrator" className="auth-logo" />
          <h1>Reset Password</h1>
          <p className="auth-subtitle">Enter your new password below</p>
        </div>

        {done ? (
          <>
            <div className="auth-ok" style={{ marginBottom: '1.5rem' }}>
              ✅ Password changed successfully!
            </div>
            <button className="btn-primary auth-submit" onClick={onDone}>
              Go to Dashboard
            </button>
          </>
        ) : (
          <form onSubmit={handleSubmit} className="auth-form">
            {error && <div className="auth-error">{error}</div>}

            <div className="auth-field">
              <label htmlFor="rp-password">New Password</label>
              <input
                id="rp-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="At least 6 characters"
                autoFocus
                required
                disabled={loading}
              />
            </div>

            <div className="auth-field">
              <label htmlFor="rp-confirm">Confirm Password</label>
              <input
                id="rp-confirm"
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                placeholder="Repeat password"
                required
                disabled={loading}
              />
            </div>

            <button type="submit" className="btn-primary auth-submit" disabled={loading}>
              {loading ? 'Saving…' : 'Set New Password'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
