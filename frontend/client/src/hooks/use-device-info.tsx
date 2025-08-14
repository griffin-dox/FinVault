import { useState, useEffect } from "react";

interface DeviceInfo {
  // Canonical fields used by backend risk engine
  browser: string; // e.g., "Chrome 139"
  os: string;      // e.g., "Windows", "macOS"
  screen: string;  // e.g., "1920x1080" (CSS px)
  timezone: string;

  // Diagnostics/extra (optional)
  userAgent: string;
  language: string;
  languages?: string[];
  platform: string;
  cookieEnabled: boolean;
  javaEnabled: boolean;

  // Rich metrics for better accuracy (optional, not required by backend)
  screenWidth?: number;
  screenHeight?: number;
  availWidth?: number;
  availHeight?: number;
  viewportWidth?: number;
  viewportHeight?: number;
  pixelRatio?: number;
  deviceClass?: 'mobile' | 'tablet' | 'desktop' | 'unknown';
  hardwareConcurrency?: number;
  deviceMemory?: number;
  touchSupport?: boolean;
}

export function useDeviceInfo(): DeviceInfo {
  const [deviceInfo, setDeviceInfo] = useState<DeviceInfo>({
    browser: "Unknown",
    os: "Unknown",
    screen: "Unknown",
    timezone: "Unknown",
    userAgent: "",
    language: "en-US",
    platform: "Unknown",
    cookieEnabled: false,
    javaEnabled: false,
  });

  useEffect(() => {
    const getBrowserInfo = async (): Promise<string> => {
      const ua = navigator.userAgent;
      // Prefer UA-CH when available
      try {
        const uaData = (navigator as any).userAgentData;
        if (uaData && typeof uaData.getHighEntropyValues === 'function') {
          const high = await uaData.getHighEntropyValues(['fullVersionList', 'uaFullVersion']);
          const list: Array<{ brand: string; version: string }> = high.fullVersionList || uaData.brands || [];
          // Prefer non-generic brands and well-known ones
          const preferred = list.find(b => /Chrome|Chromium|Edge|Opera|Firefox|Safari/i.test(b.brand)) || list[0];
          if (preferred) {
            const major = parseInt((preferred.version || '').split('.')[0] || '0', 10);
            const brand = preferred.brand.replace('Google ', '').replace('Microsoft ', '');
            return `${brand} ${isNaN(major) ? preferred.version : major}`.trim();
          }
        }
      } catch {}
      // Fallback to UA parsing
      if (ua.includes('Chrome') && !ua.includes('Edg')) {
        const version = ua.match(/Chrome\/(\d+)/)?.[1] || 'Unknown';
        return `Chrome ${version}`;
      } else if (ua.includes('Firefox')) {
        const version = ua.match(/Firefox\/(\d+)/)?.[1] || 'Unknown';
        return `Firefox ${version}`;
      } else if (ua.includes('Safari') && !ua.includes('Chrome')) {
        const version = ua.match(/Version\/(\d+)/)?.[1] || 'Unknown';
        return `Safari ${version}`;
      } else if (ua.includes('Edg')) {
        const version = ua.match(/Edg\/(\d+)/)?.[1] || 'Unknown';
        return `Edge ${version}`;
      }
      return 'Unknown Browser';
    };

    const getOSInfo = async (): Promise<string> => {
      // Prefer UA-CH platform
      try {
        const uaData = (navigator as any).userAgentData;
        if (uaData && typeof uaData.getHighEntropyValues === 'function') {
          const high = await uaData.getHighEntropyValues(['platform', 'platformVersion']);
          if (high.platform) {
            const plat = String(high.platform);
            if (/Windows/i.test(plat)) return 'Windows';
            if (/mac/i.test(plat)) return 'macOS';
            if (/android/i.test(plat)) return 'Android';
            if (/ios|iphone|ipad/i.test(plat)) return 'iOS';
            if (/linux/i.test(plat)) return 'Linux';
            return plat;
          }
        }
      } catch {}
      // UA fallback
      const userAgent = navigator.userAgent;
      if (userAgent.includes('Windows NT')) return 'Windows';
      if (userAgent.includes('Mac OS X')) return 'macOS';
      if (userAgent.includes('Android')) return 'Android';
      if (userAgent.includes('iPhone') || userAgent.includes('iPad')) return 'iOS';
      if (userAgent.includes('Linux')) return 'Linux';
      return 'Unknown OS';
    };

    const getScreenInfo = (): string => {
      return `${screen.width}x${screen.height}`;
    };

    const getTimezone = (): string => {
      try {
        return Intl.DateTimeFormat().resolvedOptions().timeZone;
      } catch (error) {
        return "Unknown";
      }
    };

    const checkJavaEnabled = (): boolean => {
      try {
        // Modern browsers don't have Java plugins by default
        return false;
      } catch (error) {
        return false;
      }
    };

    (async () => {
      const screenWidth = screen.width;
      const screenHeight = screen.height;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const pr = window.devicePixelRatio || 1;
      const minSide = Math.min(screenWidth, screenHeight);
      const deviceClass: DeviceInfo['deviceClass'] = minSide < 500 ? 'mobile' : (minSide < 900 ? 'tablet' : 'desktop');
      const info: DeviceInfo = {
        browser: await getBrowserInfo(),
        os: await getOSInfo(),
        screen: `${screenWidth}x${screenHeight}`,
        timezone: getTimezone(),
        userAgent: navigator.userAgent,
        language: navigator.language || 'en-US',
        languages: (navigator.languages || []) as string[],
        platform: navigator.platform || 'Unknown',
        cookieEnabled: navigator.cookieEnabled,
        javaEnabled: checkJavaEnabled(),
        screenWidth,
        screenHeight,
        availWidth: screen.availWidth,
        availHeight: screen.availHeight,
        viewportWidth,
        viewportHeight,
        pixelRatio: pr,
        deviceClass,
        hardwareConcurrency: (navigator as any).hardwareConcurrency,
        deviceMemory: (navigator as any).deviceMemory,
        touchSupport: ('maxTouchPoints' in navigator) ? (navigator as any).maxTouchPoints > 0 : 'ontouchstart' in window,
      };
      setDeviceInfo(info);
    })();
  }, []);

  return deviceInfo;
}

// Hook to generate a simple device fingerprint
export function useDeviceFingerprint(): string {
  const deviceInfo = useDeviceInfo();
  
  const fingerprint = btoa(
    JSON.stringify({
      browser: deviceInfo.browser,
      os: deviceInfo.os,
      screen: deviceInfo.screen,
      timezone: deviceInfo.timezone,
      language: deviceInfo.language,
      platform: deviceInfo.platform,
      cookieEnabled: deviceInfo.cookieEnabled,
    })
  );

  return fingerprint;
}
