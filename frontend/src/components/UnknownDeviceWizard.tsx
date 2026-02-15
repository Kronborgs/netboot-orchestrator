import React, { useState, useEffect } from 'react';
import { apiFetch } from '../api/client';

interface UnknownDevice {
  mac: string;
  device_type?: string;
  boot_time: string;
  status: string;
}

interface Image {
  id: string;
  name: string;
  device_type: string;
  size_gb: number;
}

interface OSFile {
  filename: string;
  path: string;
}

export const UnknownDeviceWizard: React.FC = () => {
  const [unknownDevices, setUnknownDevices] = useState<UnknownDevice[]>([]);
  const [images, setImages] = useState<Image[]>([]);
  const [osFiles, setOsFiles] = useState<OSFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<UnknownDevice | null>(null);
  const [step, setStep] = useState(0);
  const [assignment, setAssignment] = useState({
    deviceType: 'raspi',
    installTarget: 'iscsi',
    selectedImage: '',
    selectedOS: ''
  });

  useEffect(() => {
    fetchUnknownDevices();
    fetchImages();
    fetchOSFiles();
  }, []);

  const fetchUnknownDevices = async () => {
    setLoading(true);
    try {
      const res = await apiFetch(`/api/v1/unknown-devices`);
      if (res.ok) {
        setUnknownDevices(await res.json());
      }
    } catch (error) {
      console.error('Failed to fetch unknown devices:', error);
    }
    setLoading(false);
  };

  const fetchImages = async () => {
    try {
      const res = await apiFetch(`/api/v1/images`);
      if (res.ok) {
        setImages(await res.json());
      }
    } catch (error) {
      console.error('Failed to fetch images:', error);
    }
  };

  const fetchOSFiles = async () => {
    try {
      const res = await apiFetch(`/api/v1/os-installers/files`);
      if (res.ok) {
        const data = await res.json();
        setOsFiles(data.files || []);
      }
    } catch (error) {
      console.error('Failed to fetch OS files:', error);
    }
  };

  const handleStartWizard = (device: UnknownDevice) => {
    setSelectedDevice(device);
    setAssignment({
      deviceType: device.device_type || 'raspi',
      installTarget: 'iscsi',
      selectedImage: '',
      selectedOS: ''
    });
    setStep(1);
  };

  const handleRegisterDevice = async () => {
    if (!selectedDevice) return;

    try {
      const res = await fetch(
        `/api/v1/unknown-devices/register?mac=${selectedDevice.mac}&device_type=${assignment.deviceType}`,
        { method: 'POST' }
      );

      if (res.ok) {
        // Create device assignment if image selected
        if (assignment.installTarget === 'iscsi' && assignment.selectedImage) {
          await apiFetch(`/api/v1/images/${assignment.selectedImage}/assign?mac=${selectedDevice.mac}`, {
            method: 'PUT'
          });
        }

        await fetchUnknownDevices();
        setSelectedDevice(null);
        setStep(0);
      }
    } catch (error) {
      console.error('Failed to register device:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filteredImages = images.filter(img => img.device_type === assignment.deviceType);

  return (
    <div className="unknown-device-wizard">
      <div className="card">
        <div className="card-title">
          🖧 Device registration and setup wizard for new devices detected during boot
        </div>

        {loading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : unknownDevices.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">✓</div>
            <h3>No unknown devices</h3>
            <p>All devices that boot are registered</p>
          </div>
        ) : (
          <div className="list-container">
            {unknownDevices.map((device) => (
              <div key={device.mac} className="list-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '12px' }}>
                <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                      {device.mac}
                    </div>
                    <div style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                      Detected: {formatDate(device.boot_time)}
                    </div>
                    <div style={{ marginTop: '4px' }}>
                      <span className="badge badge-warning">
                        ⚠️ Unregistered
                      </span>
                    </div>
                  </div>
                  <button
                    className="btn-primary"
                    onClick={() => handleStartWizard(device)}
                  >
                    Setup Device
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Wizard Modal */}
      {selectedDevice && (
        <div className="modal-overlay active">
          <div className="modal" style={{ maxWidth: '600px' }}>
            <div className="modal-header">Device Registration Wizard</div>

            <div style={{ marginBottom: '24px', padding: '12px', background: 'var(--bg-tertiary)', borderRadius: '6px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>MAC Address</div>
              <div style={{ fontSize: '14px', fontWeight: '600', fontFamily: 'monospace', marginTop: '4px' }}>
                {selectedDevice.mac}
              </div>
            </div>

            {step === 1 && (
              <div>
                <h4 style={{ marginBottom: '16px' }}>Step 1: Select Device Type</h4>
                
                <div className="form-group">
                  <label>What type of device is this?</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginTop: '12px' }}>
                    {['raspi', 'x86', 'x64'].map((type) => (
                      <div
                        key={type}
                        onClick={() => setAssignment({ ...assignment, deviceType: type })}
                        style={{
                          padding: '16px',
                          border: `2px solid ${assignment.deviceType === type ? 'var(--primary-blue)' : 'var(--border-color)'}`,
                          borderRadius: '8px',
                          cursor: 'pointer',
                          textAlign: 'center',
                          background: assignment.deviceType === type ? 'rgba(0, 102, 204, 0.1)' : 'var(--bg-tertiary)',
                          transition: 'all 0.2s'
                        }}
                      >
                        <div style={{ fontSize: '20px', marginBottom: '4px' }}>
                          {type === 'raspi' && '🥧'}
                          {type === 'x86' && '💻'}
                          {type === 'x64' && '🖥️'}
                        </div>
                        <div style={{ fontSize: '14px', fontWeight: '500' }}>
                          {type === 'raspi' && 'Raspberry Pi'}
                          {type === 'x86' && 'x86'}
                          {type === 'x64' && 'x64'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="modal-footer" style={{ marginTop: '24px' }}>
                  <button className="btn-outline" onClick={() => { setSelectedDevice(null); setStep(0); }}>
                    Cancel
                  </button>
                  <button className="btn-primary" onClick={() => setStep(2)}>
                    Next
                  </button>
                </div>
              </div>
            )}

            {step === 2 && (
              <div>
                <h4 style={{ marginBottom: '16px' }}>Step 2: Choose Installation Target</h4>
                
                <div className="form-group">
                  <label>Where should the OS be installed?</label>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', marginTop: '12px' }}>
                    {[
                      { id: 'iscsi', label: 'iSCSI Image', icon: '💿' },
                      { id: 'local', label: 'Local Disk', icon: '💾' }
                    ].map((target) => (
                      <div
                        key={target.id}
                        onClick={() => setAssignment({ ...assignment, installTarget: target.id })}
                        style={{
                          padding: '16px',
                          border: `2px solid ${assignment.installTarget === target.id ? 'var(--primary-blue)' : 'var(--border-color)'}`,
                          borderRadius: '8px',
                          cursor: 'pointer',
                          textAlign: 'center',
                          background: assignment.installTarget === target.id ? 'rgba(0, 102, 204, 0.1)' : 'var(--bg-tertiary)',
                          transition: 'all 0.2s'
                        }}
                      >
                        <div style={{ fontSize: '24px', marginBottom: '8px' }}>{target.icon}</div>
                        <div style={{ fontSize: '14px', fontWeight: '500' }}>{target.label}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="modal-footer" style={{ marginTop: '24px' }}>
                  <button className="btn-outline" onClick={() => setStep(1)}>
                    Back
                  </button>
                  <button className="btn-primary" onClick={() => setStep(3)}>
                    Next
                  </button>
                </div>
              </div>
            )}

            {step === 3 && (
              <div>
                <h4 style={{ marginBottom: '16px' }}>
                  Step 3: {assignment.installTarget === 'iscsi' ? 'Select iSCSI Image' : 'Select OS Installer'}
                </h4>
                
                {assignment.installTarget === 'iscsi' ? (
                  <div className="form-group">
                    <label>Available iSCSI Images for {assignment.deviceType}</label>
                    {filteredImages.length === 0 ? (
                      <div style={{ padding: '16px', background: 'var(--bg-tertiary)', borderRadius: '6px', color: 'var(--text-secondary)' }}>
                        No images available for this device type. Create one first.
                      </div>
                    ) : (
                      <select
                        value={assignment.selectedImage}
                        onChange={(e) => setAssignment({ ...assignment, selectedImage: e.target.value })}
                        style={{ marginTop: '8px' }}
                      >
                        <option value="">Choose an image...</option>
                        {filteredImages.map((img) => (
                          <option key={img.id} value={img.id}>
                            {img.name} ({img.size_gb} GB)
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                ) : (
                  <div className="form-group">
                    <label>Available OS Installers</label>
                    {osFiles.length === 0 ? (
                      <div style={{ padding: '16px', background: 'var(--bg-tertiary)', borderRadius: '6px', color: 'var(--text-secondary)' }}>
                        No OS installers uploaded yet.
                      </div>
                    ) : (
                      <select
                        value={assignment.selectedOS}
                        onChange={(e) => setAssignment({ ...assignment, selectedOS: e.target.value })}
                        style={{ marginTop: '8px' }}
                      >
                        <option value="">Choose an OS...</option>
                        {osFiles.map((os) => (
                          <option key={os.path} value={os.path}>
                            {os.filename}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                )}

                <div className="modal-footer" style={{ marginTop: '24px' }}>
                  <button className="btn-outline" onClick={() => setStep(2)}>
                    Back
                  </button>
                  <button 
                    className="btn-success" 
                    onClick={handleRegisterDevice}
                    disabled={
                      assignment.installTarget === 'iscsi' 
                        ? !assignment.selectedImage
                        : !assignment.selectedOS
                    }
                  >
                    Register Device
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
