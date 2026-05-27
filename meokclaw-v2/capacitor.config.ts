import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.meokclaw.app',
  appName: 'MeokClaw',
  webDir: 'dist',
  server: {
    // Allow cleartext HTTP to local API
    allowNavigation: ['192.168.50.105', 'localhost'],
  },
  android: {
    // Allow HTTP (not just HTTPS) for local API
    allowMixedContent: true,
  },
  ios: {
    // Allow arbitrary loads for local development
    allowsLinkPreview: true,
    contentInset: 'always',
  },
};

export default config;
