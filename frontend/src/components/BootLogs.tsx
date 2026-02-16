import React, { useState, useEffect, useRef } from 'react';
import { apiFetch } from '../api/client';

interface BootLogEntry {
  mac: string;
  event: string;
  details: string;
  ip: string;
  timestamp: string;
}

export const BootLogs: React.FC = () => {
  const [logs, setLogs] = useState<BootLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterMac, setFilterMac] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchLogs();
  }, [filterMac]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, [autoRefresh, filterMac]);

  const fetchLogs = async () => {
    try {
      const macParam = filterMac ? `&mac=${encodeURIComponent(filterMac)}` : '';
      const res = await apiFetch(`/api/v1/boot/logs?limit=200${macParam}`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
      }
    } catch (e) {
      console.error('Failed to fetch boot logs:', e);
    }
  };

  const eventColor = (event: string): string => {
    if (event.includes('create')) return '#51cf66';
    if (event.includes('link')) return '#339af0';
    if (event.includes('unlink')) return '#ff922b';
    if (event.includes('boot')) return '#cc5de8';
    if (event.includes('menu')) return '#868e96';
    if (event.includes('error') || event.includes('fail')) return '#ff6b6b';
    return '#ced4da';
  };

  const eventIcon = (event: string): string => {
    if (event.includes('create')) return '💿';
    if (event.includes('link')) return '🔗';
    if (event.includes('unlink')) return '🔓';
    if (event.includes('boot')) return '🚀';
    if (event.includes('menu')) return '📋';
    if (event.includes('check')) return '✅';
    return '📄';
  };

  const formatTime = (ts: string): string => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return ts;
    }
  };

  const formatDate = (ts: string): string => {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString('en-GB', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  // Get unique MACs for filter
  const uniqueMacs = [...new Set(logs.map(l => l.mac))].sort();

  return (
    <div className="boot-logs">
      <div className="card" style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div className="card-title" style={{ margin: 0 }}>
            📡 Boot Activity Log
            <span style={{ fontSize: '14px', fontWeight: 'normal', color: 'var(--text-secondary)', marginLeft: '12px' }}>
              {logs.length} events
            </span>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <select
              value={filterMac}
              onChange={(e) => setFilterMac(e.target.value)}
              style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border-color)', background: 'var(--bg-tertiary)', color: 'var(--text-primary)', fontSize: '13px' }}
            >
              <option value="">All devices</option>
              {uniqueMacs.map(mac => (
                <option key={mac} value={mac}>{mac}</option>
              ))}
            </select>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
              Auto-refresh
            </label>
            <button className="btn-outline btn-small" onClick={fetchLogs}>
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        {logs.length === 0 ? (
          <div className="empty-state" style={{ padding: '48px' }}>
            <div className="empty-state-icon">📡</div>
            <h3>No boot events yet</h3>
            <p>Boot events will appear here when devices PXE boot from the network</p>
          </div>
        ) : (
          <div style={{ maxHeight: '600px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'var(--bg-tertiary)', position: 'sticky', top: 0, zIndex: 1 }}>
                  <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)' }}>Time</th>
                  <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)' }}>Device</th>
                  <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)' }}>Event</th>
                  <th style={{ padding: '10px 16px', textAlign: 'left', fontWeight: 600, color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '8px 16px', whiteSpace: 'nowrap', color: 'var(--text-secondary)' }}>
                      <div>{formatTime(log.timestamp)}</div>
                      <div style={{ fontSize: '11px', opacity: 0.7 }}>{formatDate(log.timestamp)}</div>
                    </td>
                    <td style={{ padding: '8px 16px', fontFamily: 'monospace', fontSize: '12px' }}>
                      {log.mac}
                    </td>
                    <td style={{ padding: '8px 16px' }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '2px 10px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: 500,
                        color: eventColor(log.event),
                        background: `${eventColor(log.event)}15`,
                      }}>
                        {eventIcon(log.event)} {log.event}
                      </span>
                    </td>
                    <td style={{ padding: '8px 16px', color: 'var(--text-secondary)', maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {log.details}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};
