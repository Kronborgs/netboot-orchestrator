import React from 'react';

export const SetupGuide: React.FC = () => {
  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px' }}>
      <h1 style={{ marginBottom: '32px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span style={{ fontSize: '32px' }}>⚙️</span>
        Netboot Setup Guide
      </h1>

      {/* Network Boot Overview */}
      <div className="card mb-4" style={{ borderLeft: '4px solid var(--primary-blue)' }}>
        <div className="card-title">🌐 What is Network Boot?</div>
        <p style={{ marginTop: '12px', lineHeight: '1.6' }}>
          Network Boot (PXE - Preboot Execution Environment) allows your devices to boot directly from a network server 
          instead of a local disk. This is perfect for Raspberry Pi (network-only) and x86/x64 systems without conventional disks.
        </p>
        <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '6px', marginTop: '12px' }}>
          <strong>Boot Flow:</strong> Device Power On → DHCP Request → Boot File Download (TFTP) → iPXE Menu → OS Installation
        </div>
      </div>

      {/* Unifi Cloud Fiber Setup */}
      <div className="card mb-4" style={{ borderLeft: '4px solid var(--success-green)' }}>
        <div className="card-title">📡 Unifi Cloud Fiber Router Configuration</div>
        
        <div style={{ marginTop: '20px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '16px', fontWeight: '600' }}>
            Step 1: Enable DHCP Server
          </h3>
          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <ol style={{ marginLeft: '20px', lineHeight: '1.8' }}>
              <li>Go to <strong>Settings → Networks → LAN</strong></li>
              <li>Select your network (e.g., <code>10.10.50.0/24</code>)</li>
              <li>Enable <strong>DHCP Server</strong> (recommended)</li>
              <li>Set DHCP Range: e.g. <code>10.10.50.6 - 10.10.50.254</code></li>
            </ol>
          </div>
        </div>

        <div style={{ marginTop: '24px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '16px', fontWeight: '600' }}>
            Step 2: Configure Network Boot (DHCP Option 67)
          </h3>
          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <ol style={{ marginLeft: '20px', lineHeight: '1.8' }}>
              <li>In the same network settings, look for <strong>Network Boot</strong></li>
              <li>Enable <strong>Network Boot</strong> toggle</li>
              <li>Set Boot Server IP: <strong>Your Netboot Orchestrator IP</strong> (e.g., <code>192.168.1.50</code>)</li>
              <li>Set Boot File (Option 67): <strong><code>undionly.kpxe</code></strong></li>
            </ol>
            <div style={{ 
              background: 'rgba(255, 152, 0, 0.1)', 
              border: '1px solid rgb(255, 152, 0)',
              padding: '12px',
              borderRadius: '6px',
              marginTop: '12px',
              fontSize: '14px'
            }}>
              ⚠️ <strong>Important:</strong> The boot file MUST be <code>undionly.kpxe</code> for BIOS systems. 
              UEFI systems may need <code>ipxe.efi</code> or <code>snponly.efi</code>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '24px' }}>
          <h3 style={{ fontSize: '16px', marginBottom: '16px', fontWeight: '600' }}>
            Step 3: Additional DHCP Settings (Recommended)
          </h3>
          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <strong>Enable:</strong>
                <ul style={{ marginLeft: '20px', marginTop: '8px' }}>
                  <li>✅ Auto Default Gateway</li>
                  <li>✅ Auto DNS Server</li>
                  <li>✅ DHCP Guarding (security)</li>
                  <li>✅ Ping Conflict Detection</li>
                </ul>
              </div>
              <div>
                <strong>Settings:</strong>
                <ul style={{ marginLeft: '20px', marginTop: '8px' }}>
                  <li>🕐 Lease Time: <code>3600</code> sec (1 hour)</li>
                  <li>📡 mDNS: Enable (optional)</li>
                  <li>⚙️ TFTP: Point to your Netboot Server</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Boot Server Setup */}
      <div className="card mb-4" style={{ borderLeft: '4px solid var(--info-color)' }}>
        <div className="card-title">🖥️ Boot Server (Netboot Orchestrator) Requirements</div>
        
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ fontSize: '14px', marginBottom: '12px', fontWeight: '600' }}>Required Services:</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '6px' }}>
              <div style={{ fontWeight: '600', marginBottom: '8px' }}>🔷 DHCP</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Handled by your router (Unifi Cloud Fiber)
              </div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '6px' }}>
              <div style={{ fontWeight: '600', marginBottom: '8px' }}>📦 TFTP Server</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Delivers iPXE boot files (port 69 UDP)
              </div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '6px' }}>
              <div style={{ fontWeight: '600', marginBottom: '8px' }}>🌐 HTTP Server</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Serves OS installers and menu (port 80)
              </div>
            </div>
            <div style={{ background: 'var(--bg-tertiary)', padding: '12px', borderRadius: '6px' }}>
              <div style={{ fontWeight: '600', marginBottom: '8px' }}>💾 iSCSI Target</div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Network disk images (port 3260)
              </div>
            </div>
          </div>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h4 style={{ fontSize: '14px', marginBottom: '12px', fontWeight: '600' }}>Boot File Chain:</h4>
          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <code style={{ display: 'block', lineHeight: '1.8', fontSize: '12px' }}>
              DHCP Option 67 → TFTP: undionly.kpxe<br/>
              &nbsp;&nbsp;↓<br/>
              undionly.kpxe loads → TFTP: boot.ipxe<br/>
              &nbsp;&nbsp;↓<br/>
              boot.ipxe fetches menu → HTTP: /api/v1/boot/menu<br/>
              &nbsp;&nbsp;↓<br/>
              User selects OS → HTTP download or iSCSI mount
            </code>
          </div>
        </div>
      </div>

      {/* Testing */}
      <div className="card mb-4" style={{ borderLeft: '4px solid var(--warning-yellow)' }}>
        <div className="card-title">🧪 Testing Your Setup</div>
        
        <div style={{ marginTop: '16px' }}>
          <h4 style={{ fontSize: '14px', marginBottom: '12px', fontWeight: '600' }}>Step-by-step Test:</h4>
          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <ol style={{ marginLeft: '20px', lineHeight: '2' }}>
              <li>Power on a device (Raspberry Pi or x86 computer) with network cable</li>
              <li>Watch for "PXE-E53: No boot filename received"? → Router isn't sending Option 67</li>
              <li>See "No TFTP server"? → Router IP for boot server is wrong</li>
              <li>Boot file loads but hangs? → Check TFTP server status</li>
              <li>iPXE menu appears? → ✅ Network boot is working!</li>
              <li>Select OS from menu → Should either download or mount iSCSI</li>
            </ol>
          </div>
        </div>

        <div style={{ marginTop: '20px' }}>
          <h4 style={{ fontSize: '14px', marginBottom: '12px', fontWeight: '600' }}>Useful Commands (from boot server):</h4>
          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px', fontSize: '12px' }}>
            <code style={{ display: 'block', marginBottom: '8px' }}>
              # Check TFTP service<br/>
              netstat -ln | grep 69
            </code>
            <code style={{ display: 'block', marginBottom: '8px' }}>
              # Monitor TFTP requests<br/>
              journalctl -u tftp -f
            </code>
            <code style={{ display: 'block' }}>
              # Check HTTP server<br/>
              curl http://localhost:8000/api/v1/version
            </code>
          </div>
        </div>
      </div>

      {/* Troubleshooting */}
      <div className="card" style={{ borderLeft: '4px solid var(--danger-red)' }}>
        <div className="card-title">🔧 Troubleshooting Common Issues</div>
        
        <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: '1fr', gap: '16px' }}>
          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <strong style={{ color: 'var(--danger-red)' }}>❌ Device won't boot from network</strong>
            <ul style={{ marginLeft: '20px', marginTop: '8px', fontSize: '14px' }}>
              <li>Check device BIOS/UEFI settings - ensure Network Boot is enabled</li>
              <li>Verify network cable is connected</li>
              <li>Check router DHCP is enabled for the device's network</li>
            </ul>
          </div>

          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <strong style={{ color: 'var(--danger-red)' }}>❌ Gets DHCP but no boot file</strong>
            <ul style={{ marginLeft: '20px', marginTop: '8px', fontSize: '14px' }}>
              <li>Check DHCP Option 67 is set to <code>undionly.kpxe</code></li>
              <li>Verify boot server IP in router matches your Netboot Orchestrator IP</li>
              <li>Test: <code>ping bootserver_ip</code> from a device on same network</li>
            </ul>
          </div>

          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <strong style={{ color: 'var(--danger-red)' }}>❌ Boot file downloads but hangs</strong>
            <ul style={{ marginLeft: '20px', marginTop: '8px', fontSize: '14px' }}>
              <li>TFTP service may not be running - check systemctl status tftp</li>
              <li>Firewall blocking UDP port 69 - check firewall rules</li>
              <li>Check TFTP directory has correct files: <code>/tftpboot/</code></li>
            </ul>
          </div>

          <div style={{ background: 'var(--bg-tertiary)', padding: '16px', borderRadius: '6px' }}>
            <strong style={{ color: 'var(--danger-red)' }}>❌ iPXE menu loads but OS download fails</strong>
            <ul style={{ marginLeft: '20px', marginTop: '8px', fontSize: '14px' }}>
              <li>Check HTTP server is running on port 80</li>
              <li>Verify OS installers are uploaded to Orchestrator</li>
              <li>Test: <code>curl http://bootserver_ip/api/v1/os-installers/files</code></li>
            </ul>
          </div>
        </div>
      </div>

      {/* Summary Card */}
      <div className="card mt-4" style={{ background: 'linear-gradient(135deg, rgba(25,118,210,0.1), rgba(66,133,244,0.1))', borderTop: '3px solid var(--primary-blue)' }}>
        <div className="card-title">✅ Setup Checklist</div>
        <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>Router DHCP enabled</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>Network Boot enabled</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>Option 67 = undionly.kpxe</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>Boot server IP correct</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>TFTP service running</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>HTTP server running</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>OS installers uploaded</span>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input type="checkbox" style={{ cursor: 'pointer' }} />
            <span>Device can reach boot server</span>
          </div>
        </div>
      </div>
    </div>
  );
};
