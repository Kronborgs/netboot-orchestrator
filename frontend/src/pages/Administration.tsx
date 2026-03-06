import React, { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '../api/client';

type AdminTab = 'users' | 'smtp' | 'audit';

interface User {
  username: string;
  role: string;
  created_at: string;
}

interface SmtpSettings {
  host: string;
  port: number;
  username: string;
  password: string;
  from_address: string;
  from_name: string;
  use_tls: boolean;
  use_ssl: boolean;
}

interface AuditEntry {
  ts: string;
  actor: string;
  action: string;
  target: string;
  detail: string;
}

// ---------------------------------------------------------------------------
// Users tab
// ---------------------------------------------------------------------------
const UsersTab: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [addError, setAddError] = useState('');
  const [adding, setAdding] = useState(false);
  const [deletingUser, setDeletingUser] = useState<string | null>(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/auth/users');
      if (!res.ok) throw new Error('Failed to load users');
      setUsers(await res.json());
    } catch {
      setError('Could not load users');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddError('');
    setAdding(true);
    try {
      const res = await apiFetch('/api/v1/auth/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newUsername.trim(), password: newPassword, role: 'admin' }),
      });
      const data = await res.json();
      if (!res.ok) { setAddError(data.detail || 'Failed to create user'); return; }
      setNewUsername('');
      setNewPassword('');
      await loadUsers();
    } catch {
      setAddError('Failed to create user');
    } finally {
      setAdding(false);
    }
  };

  const handleDelete = async (username: string) => {
    if (!window.confirm(`Delete user "${username}"?`)) return;
    setDeletingUser(username);
    try {
      await apiFetch(`/api/v1/auth/users/${encodeURIComponent(username)}`, { method: 'DELETE' });
      await loadUsers();
    } finally {
      setDeletingUser(null);
    }
  };

  return (
    <div className="admin-section">
      <h2 className="admin-section-title">User Accounts</h2>
      <p className="admin-section-desc">
        All users have full admin access. The audit log records who did what.
      </p>

      {error && <div className="admin-error">{error}</div>}

      {loading ? (
        <p className="admin-loading">Loading…</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr><th>Username</th><th>Role</th><th>Created</th><th></th></tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.username}>
                <td><span className="admin-username">👤 {u.username}</span></td>
                <td><span className="admin-badge">{u.role}</span></td>
                <td className="admin-date">{new Date(u.created_at).toLocaleString()}</td>
                <td>
                  <button
                    className="btn-danger-sm"
                    onClick={() => handleDelete(u.username)}
                    disabled={deletingUser === u.username}
                  >
                    {deletingUser === u.username ? '…' : 'Delete'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="admin-card" style={{ marginTop: '2rem' }}>
        <h3>Add Admin User</h3>
        <form onSubmit={handleAddUser} className="admin-form-row">
          {addError && <div className="admin-error" style={{ gridColumn: '1/-1' }}>{addError}</div>}
          <div className="admin-field">
            <label>Username</label>
            <input
              type="text"
              value={newUsername}
              onChange={e => setNewUsername(e.target.value)}
              placeholder="new-admin"
              required
              minLength={3}
              disabled={adding}
            />
          </div>
          <div className="admin-field">
            <label>Password</label>
            <input
              type="password"
              value={newPassword}
              onChange={e => setNewPassword(e.target.value)}
              placeholder="at least 6 chars"
              required
              minLength={6}
              disabled={adding}
            />
          </div>
          <div className="admin-field admin-field--action">
            <label>&nbsp;</label>
            <button type="submit" className="btn-primary" disabled={adding}>
              {adding ? 'Adding…' : 'Add User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// SMTP tab
// ---------------------------------------------------------------------------
const SmtpTab: React.FC = () => {
  const [settings, setSettings] = useState<SmtpSettings>({
    host: '', port: 587, username: '', password: '',
    from_address: '', from_name: 'Netboot Orchestrator',
    use_tls: true, use_ssl: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testTo, setTestTo] = useState('');
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  useEffect(() => {
    apiFetch('/api/v1/settings/smtp')
      .then(r => r.json())
      .then(d => setSettings(s => ({ ...s, ...d })))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      const res = await apiFetch('/api/v1/settings/smtp', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      if (!res.ok) { const d = await res.json(); setMsg({ type: 'err', text: d.detail || 'Save failed' }); return; }
      setMsg({ type: 'ok', text: 'SMTP settings saved.' });
    } catch {
      setMsg({ type: 'err', text: 'Save failed' });
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!testTo.trim()) { setMsg({ type: 'err', text: 'Enter a recipient email address first' }); return; }
    setTesting(true);
    setMsg(null);
    try {
      const res = await apiFetch('/api/v1/settings/smtp/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to: testTo.trim() }),
      });
      const d = await res.json();
      if (!res.ok) { setMsg({ type: 'err', text: d.detail || 'Test failed' }); return; }
      setMsg({ type: 'ok', text: `✅ Test email sent to ${d.sent_to}` });
    } catch {
      setMsg({ type: 'err', text: 'Test failed — check network' });
    } finally {
      setTesting(false);
    }
  };

  if (loading) return <p className="admin-loading">Loading…</p>;

  const field = (label: string, key: keyof SmtpSettings, type = 'text', placeholder = '') => (
    <div className="admin-field">
      <label>{label}</label>
      <input
        type={type}
        value={settings[key] as string}
        placeholder={placeholder}
        onChange={e => setSettings(s => ({ ...s, [key]: type === 'number' ? Number(e.target.value) : e.target.value }))}
        disabled={saving}
      />
    </div>
  );

  return (
    <div className="admin-section">
      <h2 className="admin-section-title">SMTP / Email Settings</h2>
      <p className="admin-section-desc">
        Configure outgoing email. Gmail example: host <code>smtp.gmail.com</code>, port <code>587</code>,
        TLS on, username = your Gmail address, password = an <strong>App Password</strong> (not your account password).
        Any SMTP server with the same settings will work.
      </p>

      {msg && (
        <div className={msg.type === 'ok' ? 'admin-ok' : 'admin-error'} style={{ marginBottom: '1rem' }}>
          {msg.text}
        </div>
      )}

      <form onSubmit={handleSave} className="admin-section">
        <div className="admin-card">
          <h3>Server</h3>
          <div className="admin-form-2col">
            {field('SMTP Host', 'host', 'text', 'smtp.gmail.com')}
            {field('Port', 'port', 'number', '587')}
            <div className="admin-field admin-field--checkbox">
              <label>
                <input type="checkbox" checked={settings.use_tls}
                  onChange={e => setSettings(s => ({ ...s, use_tls: e.target.checked, use_ssl: e.target.checked ? false : s.use_ssl }))} />
                {' '}STARTTLS (recommended, port 587)
              </label>
            </div>
            <div className="admin-field admin-field--checkbox">
              <label>
                <input type="checkbox" checked={settings.use_ssl}
                  onChange={e => setSettings(s => ({ ...s, use_ssl: e.target.checked, use_tls: e.target.checked ? false : s.use_tls }))} />
                {' '}SSL/TLS (legacy, port 465)
              </label>
            </div>
          </div>
        </div>

        <div className="admin-card">
          <h3>Authentication</h3>
          <div className="admin-form-2col">
            {field('Username', 'username', 'text', 'you@gmail.com')}
            {field('Password / App Password', 'password', 'password', '••••••••')}
          </div>
        </div>

        <div className="admin-card">
          <h3>Sender</h3>
          <div className="admin-form-2col">
            {field('From Address', 'from_address', 'email', 'netboot@yourdomain.com')}
            {field('From Name', 'from_name', 'text', 'Netboot Orchestrator')}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flex: 1, minWidth: 240 }}>
            <input
              type="email"
              className="smtp-test-input"
              placeholder="Send test email to…"
              value={testTo}
              onChange={e => setTestTo(e.target.value)}
            />
            <button type="button" className="btn-secondary" onClick={handleTest} disabled={testing || saving}>
              {testing ? 'Sending…' : 'Send Test'}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Audit log tab
// ---------------------------------------------------------------------------
const AuditTab: React.FC = () => {
  const [log, setLog] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    apiFetch('/api/v1/audit-log?limit=200')
      .then(r => r.json())
      .then(d => setLog(Array.isArray(d) ? d : []))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const ACTION_ICON: Record<string, string> = {
    'user.created': '➕',
    'user.deleted': '🗑️',
    'smtp.updated': '📧',
    'smtp.test_sent': '📤',
  };

  return (
    <div className="admin-section">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 className="admin-section-title" style={{ margin: 0 }}>Audit Log</h2>
        <button className="btn-secondary" onClick={load} disabled={loading}>↺ Refresh</button>
      </div>
      <p className="admin-section-desc">
        Records admin actions: user creation/deletion, SMTP changes, and test emails.
        Future versions will log device assignments and image management.
      </p>
      {loading ? (
        <p className="admin-loading">Loading…</p>
      ) : log.length === 0 ? (
        <p className="admin-loading">No entries yet.</p>
      ) : (
        <table className="admin-table">
          <thead>
            <tr><th>Time</th><th>Actor</th><th>Action</th><th>Target</th><th>Detail</th></tr>
          </thead>
          <tbody>
            {log.map((e, i) => (
              <tr key={i}>
                <td className="admin-date">{new Date(e.ts).toLocaleString()}</td>
                <td><span className="admin-username">👤 {e.actor}</span></td>
                <td><span className="audit-action">{ACTION_ICON[e.action] || '•'} {e.action}</span></td>
                <td>{e.target}</td>
                <td className="audit-detail">{e.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main Administration page
// ---------------------------------------------------------------------------
export const Administration: React.FC = () => {
  const [tab, setTab] = useState<AdminTab>('users');

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>🔐 Administration</h1>
        <p>Manage users, configure email, and review the audit log.</p>
      </div>

      <div className="admin-tabs">
        {(['users', 'smtp', 'audit'] as AdminTab[]).map(t => (
          <button
            key={t}
            className={`admin-tab-btn ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {{ users: '👥 Users', smtp: '📧 SMTP / Email', audit: '📋 Audit Log' }[t]}
          </button>
        ))}
      </div>

      <div className="admin-content">
        {tab === 'users' && <UsersTab />}
        {tab === 'smtp'  && <SmtpTab />}
        {tab === 'audit' && <AuditTab />}
      </div>
    </div>
  );
};
