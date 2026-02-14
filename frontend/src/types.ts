export interface Device {
  mac: string;
  device_type: 'raspi' | 'x86' | 'x64';
  name: string;
  enabled: boolean;
  image_id?: string;
  kernel_set?: string;
}

export interface Image {
  id: string;
  name: string;
  size_gb: number;
  device_type: 'raspi' | 'x86' | 'x64';
  assigned_to?: string;
  created_at?: string;
}

export interface KernelSet {
  name: string;
  kernel_url: string;
  initramfs_url?: string;
  is_default?: boolean;
}

export interface OSInstaller {
  name: string;
  path: string;
  kernel: string;
  initrd: string;
  kernel_cmdline: string;
  device_type: 'raspi' | 'x86' | 'x64';
}
