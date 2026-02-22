import React, { useState, useEffect } from 'react';
import { apiFetch, getApiUrl } from '../api/client';

interface Device {
  mac: string;
  device_type: string;
  name: string;
  enabled: boolean;
  image_id?: string;
  kernel_set: string;
}

interface DeviceMetrics {
  mac: string;
  name?: string;
  image_id?: string;
  linked?: boolean;
  message?: string;
  connection?: {
    active: boolean;
    session_count: number;
    remote_ips: string[];
  };
  disk_io?: {
    read_bytes: number;
    write_bytes: number;
    source: string;
  };
  network?: {
    rx_bytes: number;
    tx_bytes: number;
    source: string;
  };
  boot_transfer?: {
    http_tx_bytes: number;
    http_requests: number;
    last_path?: string;
    last_seen?: string;
    last_remote_ip?: string;
    session_started_at?: string;
  };
  install_progress?: {
    active_session: boolean;
    stalled: boolean;
    stall_seconds: number;
    threshold_seconds: number;
    last_progress_at?: string;
    observed_total_bytes?: number;
    observed_source?: string;
  };
  warning?: string;
}

interface DeviceLog {
  mac: string;
  event: string;
  details: string;
  timestamp: string;
}

interface DeviceRateSample {
  timestampMs: number;
  readBytes?: number;
  writeBytes?: number;
  rxBytes?: number;
  txBytes?: number;
}

interface DeviceRates {
  diskReadMBps?: number;
  diskWriteMBps?: number;
  inboundMbps?: number;
  outboundMbps?: number;
}

interface WinpeLogFile {
  name: string;
  size_bytes: number;
  modified_at: number;
}

export const DeviceList: React.FC = () => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [expandedMac, setExpandedMac] = useState<string | null>(null);
  const [metricsByMac, setMetricsByMac] = useState<Record<string, DeviceMetrics>>({});
  const [ratesByMac, setRatesByMac] = useState<Record<string, DeviceRates>>({});
  const [logsByMac, setLogsByMac] = useState<Record<string, DeviceLog[]>>({});
  const [winpeLogsByMac, setWinpeLogsByMac] = useState<Record<string, WinpeLogFile[]>>({});
  const [detailsLoadingByMac, setDetailsLoadingByMac] = useState<Record<string, boolean>>({});
  const [previousSamplesByMac, setPreviousSamplesByMac] = useState<Record<string, DeviceRateSample>>({});
  const [formData, setFormData] = useState({
    mac: '',
    device_type: 'raspi',
    name: '',
    enabled: true
  });

  useEffect(() => {
    fetchDevices();
  }, []);

  useEffect(() => {
    let source: EventSource | null = null;
    let fallbackPoller: ReturnType<typeof setInterval> | null = null;

    const startFallbackPolling = () => {
      if (fallbackPoller) return;
      fallbackPoller = setInterval(() => {
        fetchDevices(true);
      }, 10000);
    };

    try {
      source = new EventSource(getApiUrl('/api/v1/devices/events'));
      source.addEventListener('devices', () => {
        fetchDevices(true);
      });
      source.onerror = () => {
        if (source) {
          source.close();
          source = null;
        }
        startFallbackPolling();
      };
    } catch (err) {
      console.warn('SSE unavailable, using polling fallback', err);
      startFallbackPolling();
    }

    return () => {
      if (source) source.close();
      if (fallbackPoller) clearInterval(fallbackPoller);
    };
  }, []);

  useEffect(() => {
    if (!expandedMac) return;

    const metricsTimer = setInterval(() => {
      fetchDeviceDetails(expandedMac, false);
    }, 3000);

    const logsTimer = setInterval(() => {
      fetchDeviceDetails(expandedMac, true);
    }, 10000);

    return () => {
      clearInterval(metricsTimer);
      clearInterval(logsTimer);
    };
  }, [expandedMac]);

  const formatBytes = (bytes?: number): string => {
    if (bytes === undefined || bytes === null || bytes < 0) return '—';
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let value = bytes;
    let idx = 0;
    while (value >= 1024 && idx < units.length - 1) {
      value /= 1024;
      idx += 1;
    }
    return `${value.toFixed(2)} ${units[idx]}`;
  };

  const formatTimestamp = (value?: string): string => {
    if (!value) return 'Unknown';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString();
  };

  const formatMBps = (value?: number): string => {
    if (value === undefined || value === null || value < 0) return '—';
    return `${value.toFixed(2)} MB/s`;
  };

  const formatMbps = (value?: number): string => {
    if (value === undefined || value === null || value < 0) return '—';
    return `${value.toFixed(1)} Mbps`;
  };

  const fetchDevices = async (silent: boolean = false) => {
    try {
      if (!silent) setLoading(true);
      const response = await apiFetch(`/api/v1/devices`);
      if (response.ok) {
        setDevices(await response.json());
        setError(null);
      }
    } catch (err) {
      setError('Failed to fetch devices');
      console.error(err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const handleCreateDevice = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await apiFetch(`/api/v1/devices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setFormData({ mac: '', device_type: 'raspi', name: '', enabled: true });
        setShowForm(false);
        fetchDevices();
      }
    } catch (err) {
      setError('Failed to create device');
      console.error(err);
    }
  };

  const deleteDevice = async (mac: string) => {
    if (!confirm('Are you sure you want to delete this device?')) return;
    try {
      const res = await apiFetch(`/api/v1/devices/${mac}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setDevices(devices.filter(d => d.mac !== mac));
      }
    } catch (err) {
      setError('Failed to delete device');
      console.error(err);
    }
  };

  const toggleDeviceStatus = async (device: Device) => {
    try {
      const res = await apiFetch(`/api/v1/devices/${device.mac}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...device, enabled: !device.enabled })
      });
      if (res.ok) {
        fetchDevices();
      }
    } catch (err) {
      setError('Failed to update device');
      console.error(err);
    }
  };

  const fetchDeviceDetails = async (mac: string, includeLogs: boolean) => {
    try {
      const requests: Promise<Response>[] = [
        apiFetch(`/api/v1/boot/devices/${encodeURIComponent(mac)}/metrics`)
      ];
      if (includeLogs) {
        requests.push(apiFetch(`/api/v1/boot/logs?mac=${encodeURIComponent(mac)}&limit=20`));
        requests.push(apiFetch(`/api/v1/boot/winpe/logs?mac=${encodeURIComponent(mac)}`));
      }

      const responses = await Promise.all(requests);
      const metricsRes = responses[0];

      if (metricsRes.ok) {
        const data = await metricsRes.json();
        const nowMs = Date.now();

        setPreviousSamplesByMac((previousSamples) => {
          const last = previousSamples[mac];
          const nextSample: DeviceRateSample = {
            timestampMs: nowMs,
            readBytes: data?.disk_io?.read_bytes,
            writeBytes: data?.disk_io?.write_bytes,
            rxBytes: data?.network?.rx_bytes,
            txBytes: data?.network?.tx_bytes,
          };

          if (last) {
            const elapsedSeconds = (nowMs - last.timestampMs) / 1000;
            if (elapsedSeconds > 0) {
              const readDelta = (nextSample.readBytes ?? NaN) - (last.readBytes ?? NaN);
              const writeDelta = (nextSample.writeBytes ?? NaN) - (last.writeBytes ?? NaN);
              const rxDelta = (nextSample.rxBytes ?? NaN) - (last.rxBytes ?? NaN);
              const txDelta = (nextSample.txBytes ?? NaN) - (last.txBytes ?? NaN);

              const diskReadMBps = Number.isFinite(readDelta) && readDelta >= 0
                ? (readDelta / elapsedSeconds) / (1024 * 1024)
                : undefined;
              const diskWriteMBps = Number.isFinite(writeDelta) && writeDelta >= 0
                ? (writeDelta / elapsedSeconds) / (1024 * 1024)
                : undefined;
              const inboundMbps = Number.isFinite(rxDelta) && rxDelta >= 0
                ? (rxDelta * 8) / elapsedSeconds / 1_000_000
                : undefined;
              const outboundMbps = Number.isFinite(txDelta) && txDelta >= 0
                ? (txDelta * 8) / elapsedSeconds / 1_000_000
                : undefined;

              setRatesByMac((currentRates) => ({
                ...currentRates,
                [mac]: {
                  diskReadMBps,
                  diskWriteMBps,
                  inboundMbps,
                  outboundMbps,
                }
              }));
            }
          }

          return {
            ...previousSamples,
            [mac]: nextSample,
          };
        });

        setMetricsByMac(prev => ({ ...prev, [mac]: data }));
      }

      if (includeLogs && responses[1] && responses[1].ok) {
        const logsData = await responses[1].json();
        setLogsByMac(prev => ({ ...prev, [mac]: logsData || [] }));
      }

      if (includeLogs && responses[2] && responses[2].ok) {
        const filesData = await responses[2].json();
        setWinpeLogsByMac(prev => ({ ...prev, [mac]: filesData || [] }));
      }
    } catch (err) {
      console.error('Failed to fetch device details', err);
    }
  };

  const buildWinpeDownloadUrl = (mac: string, name: string): string => {
    const base = `${window.location.protocol}//${window.location.hostname}:8000`;
    return `${base}/api/v1/boot/winpe/logs/download?mac=${encodeURIComponent(mac)}&name=${encodeURIComponent(name)}`;
  };

  const toggleDetails = async (mac: string) => {
    if (expandedMac === mac) {
      setExpandedMac(null);
      return;
    }

    setExpandedMac(mac);
    if (metricsByMac[mac] && logsByMac[mac] && winpeLogsByMac[mac]) {
      return;
    }

    setDetailsLoadingByMac(prev => ({ ...prev, [mac]: true }));
    try {
      await fetchDeviceDetails(mac, true);
    } finally {
      setDetailsLoadingByMac(prev => ({ ...prev, [mac]: false }));
    }
  };

  if (error) {
    return <div className="card" style={{ color: 'var(--danger-color)' }}>❌ {error}</div>;
  }

  return (
    <div className="device-list">
      <div className="card">
        <button 
          className="btn-primary mb-3"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? 'Cancel' : '+ Register New Device'}
        </button>

        {showForm && (
          <form onSubmit={handleCreateDevice} className="card mb-3" style={{ background: 'var(--bg-tertiary)' }}>
            <h3>Register New Device</h3>
            
            <div className="form-group">
              <label>MAC Address</label>
              <input
                type="text"
                value={formData.mac}
                onChange={(e) => setFormData({ ...formData, mac: e.target.value })}
                placeholder="e.g., 00:1A:2B:3C:4D:5E"
                required
              />
            </div>

            <div className="form-row">
              <div className="form-group">
                <label>Device Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., RaspberryPi-01"
                  required
                />
              </div>

              <div className="form-group">
                <label>Device Type</label>
                <select
                  value={formData.device_type}
                  onChange={(e) => setFormData({ ...formData, device_type: e.target.value })}
                  required
                >
                  <option value="raspi">Raspberry Pi</option>
                  <option value="x86">x86</option>
                  <option value="x64">x64</option>
                </select>
              </div>
            </div>

            <button type="submit" className="btn-success">
              Register Device
            </button>
          </form>
        )}
      </div>

      {loading ? (
        <div className="loading">
          <div className="spinner"></div>
        </div>
      ) : devices.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📭</div>
            <h3>No devices registered</h3>
            <p>Register your first device to get started</p>
          </div>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>MAC Address</th>
              <th>Name</th>
              <th>Type</th>
              <th>Status</th>
              <th>Image</th>
              <th style={{ width: '220px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <React.Fragment key={device.mac}>
                <tr>
                  <td style={{ fontFamily: 'monospace', fontSize: '12px' }}>{device.mac}</td>
                  <td>{device.name}</td>
                  <td>
                    <span style={{ fontSize: '16px' }}>
                      {device.device_type === 'raspi' && '🥧'}
                      {device.device_type === 'x86' && '💻'}
                      {device.device_type === 'x64' && '🖥️'}
                    </span>
                    {' '}{device.device_type.toUpperCase()}
                  </td>
                  <td>
                    <span className={`badge ${device.enabled ? 'badge-success' : 'badge-danger'}`}>
                      {device.enabled ? '✓ Active' : '⊘ Inactive'}
                    </span>
                  </td>
                  <td>
                    {device.image_id ? (
                      <span className="badge badge-info">{device.image_id}</span>
                    ) : (
                      <span style={{ color: 'var(--text-secondary)' }}>—</span>
                    )}
                  </td>
                  <td style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    <button
                      className="btn-small"
                      onClick={() => toggleDetails(device.mac)}
                      style={{
                        background: expandedMac === device.mac ? 'var(--primary-blue)' : 'var(--bg-tertiary)',
                        color: 'white',
                        border: 'none',
                        padding: '4px 8px',
                        fontSize: '12px'
                      }}
                    >
                      {expandedMac === device.mac ? 'Hide Details' : 'Details'}
                    </button>
                    <button
                      className="btn-small"
                      onClick={() => toggleDeviceStatus(device)}
                      style={{
                        background: device.enabled ? 'var(--accent-orange)' : 'var(--success-color)',
                        color: 'white',
                        border: 'none',
                        padding: '4px 8px',
                        fontSize: '12px'
                      }}
                    >
                      {device.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      className="btn-danger btn-small"
                      onClick={() => deleteDevice(device.mac)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
                {expandedMac === device.mac && (
                  <tr>
                    <td colSpan={6} style={{ background: 'var(--bg-tertiary)', padding: '12px 16px' }}>
                      {detailsLoadingByMac[device.mac] ? (
                        <div style={{ color: 'var(--text-secondary)' }}>Loading device metrics and logs...</div>
                      ) : (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                          <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px' }}>
                            <div style={{ fontWeight: 600, marginBottom: '8px' }}>Connection Metrics</div>
                            {metricsByMac[device.mac] ? (
                              <>
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                                  Session: {metricsByMac[device.mac]?.connection?.active ? 'Active' : 'Inactive'}
                                  {' • '}Count: {metricsByMac[device.mac]?.connection?.session_count ?? 0}
                                </div>
                                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                  Remote IPs: {(metricsByMac[device.mac]?.connection?.remote_ips || []).join(', ') || '—'}
                                </div>
                                <div style={{ marginTop: '8px', fontSize: '13px' }}>
                                  Disk I/O: Read {formatMBps(ratesByMac[device.mac]?.diskReadMBps)} / Write {formatMBps(ratesByMac[device.mac]?.diskWriteMBps)}
                                </div>
                                <div style={{ marginTop: '4px', fontSize: '13px' }}>
                                  Network: Inbound {formatMbps(ratesByMac[device.mac]?.inboundMbps)} / Outbound {formatMbps(ratesByMac[device.mac]?.outboundMbps)}
                                </div>
                                <div style={{ marginTop: '4px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                  Cumulative: Disk R {formatBytes(metricsByMac[device.mac]?.disk_io?.read_bytes)} / W {formatBytes(metricsByMac[device.mac]?.disk_io?.write_bytes)}; Net RX {formatBytes(metricsByMac[device.mac]?.network?.rx_bytes)} / TX {formatBytes(metricsByMac[device.mac]?.network?.tx_bytes)}
                                </div>
                                {!!metricsByMac[device.mac]?.boot_transfer && (
                                  <div style={{ marginTop: '8px', fontSize: '13px' }}>
                                    WinPE HTTP: TX {formatBytes(metricsByMac[device.mac]?.boot_transfer?.http_tx_bytes)}
                                    {' | '}Requests {metricsByMac[device.mac]?.boot_transfer?.http_requests ?? 0}
                                  </div>
                                )}
                                {!!metricsByMac[device.mac]?.boot_transfer?.last_path && (
                                  <div style={{ marginTop: '4px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                    Last file: {metricsByMac[device.mac]?.boot_transfer?.last_path}
                                  </div>
                                )}
                                {!!metricsByMac[device.mac]?.boot_transfer?.last_seen && (
                                  <div style={{ marginTop: '2px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                    Last transfer: {formatTimestamp(metricsByMac[device.mac]?.boot_transfer?.last_seen)}
                                  </div>
                                )}
                                {!!metricsByMac[device.mac]?.boot_transfer?.session_started_at && (
                                  <div style={{ marginTop: '2px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                    Session started: {formatTimestamp(metricsByMac[device.mac]?.boot_transfer?.session_started_at)}
                                  </div>
                                )}
                                {!!metricsByMac[device.mac]?.install_progress && (
                                  <div style={{ marginTop: '4px', fontSize: '12px', color: metricsByMac[device.mac]?.install_progress?.stalled ? 'var(--warning-color)' : 'var(--text-secondary)' }}>
                                    Install progress: {metricsByMac[device.mac]?.install_progress?.active_session ? 'Session active' : 'Session inactive'}
                                    {' • '}Stalled: {metricsByMac[device.mac]?.install_progress?.stalled ? 'Yes' : 'No'}
                                    {' • '}Idle for: {metricsByMac[device.mac]?.install_progress?.stall_seconds ?? 0}s
                                  </div>
                                )}
                                <div style={{ marginTop: '4px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                                  Sources: disk={metricsByMac[device.mac]?.disk_io?.source || 'unknown'}, net={metricsByMac[device.mac]?.network?.source || 'unknown'}
                                </div>
                                {metricsByMac[device.mac]?.warning && (
                                  <div style={{ marginTop: '8px', color: 'var(--warning-color)', fontSize: '12px' }}>
                                    {metricsByMac[device.mac]?.warning}
                                  </div>
                                )}
                                {metricsByMac[device.mac]?.message && (
                                  <div style={{ marginTop: '8px', color: 'var(--text-secondary)', fontSize: '12px' }}>
                                    {metricsByMac[device.mac]?.message}
                                  </div>
                                )}
                              </>
                            ) : (
                              <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>No metrics available.</div>
                            )}
                          </div>

                          <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px' }}>
                            <div style={{ fontWeight: 600, marginBottom: '8px' }}>Device Logs (MAC)</div>
                            {(winpeLogsByMac[device.mac] || []).length > 0 && (
                              <div style={{ marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid var(--border-color)' }}>
                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                                  WinPE log files
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                                  {(winpeLogsByMac[device.mac] || []).map((file) => (
                                    <a
                                      key={file.name}
                                      href={buildWinpeDownloadUrl(device.mac, file.name)}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="btn-small"
                                      style={{
                                        background: 'var(--primary-blue)',
                                        color: 'white',
                                        border: 'none',
                                        padding: '4px 8px',
                                        fontSize: '12px',
                                        textDecoration: 'none'
                                      }}
                                    >
                                      Download {file.name} ({formatBytes(file.size_bytes)})
                                    </a>
                                  ))}
                                </div>
                              </div>
                            )}
                            {(winpeLogsByMac[device.mac] || []).length === 0 && (
                              <div style={{ marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', fontSize: '12px' }}>
                                WinPE logs not uploaded yet (startnet.log or setupact.log will appear here after WinPE starts).
                              </div>
                            )}
                            {(logsByMac[device.mac] || []).length === 0 ? (
                              <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>No logs for this device.</div>
                            ) : (
                              <div style={{ maxHeight: '220px', overflowY: 'auto', fontSize: '12px' }}>
                                {(logsByMac[device.mac] || []).map((entry, idx) => (
                                  <div key={idx} style={{ padding: '6px 0', borderBottom: '1px solid var(--border-color)' }}>
                                    <div style={{ color: 'var(--text-secondary)' }}>{formatTimestamp(entry.timestamp)}</div>
                                    <div><strong>{entry.event}</strong> — {entry.details || 'No details'}</div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
