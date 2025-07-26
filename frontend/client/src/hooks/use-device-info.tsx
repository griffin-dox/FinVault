import { useState, useEffect } from "react";

interface DeviceInfo {
  browser: string;
  os: string;
  screen: string;
  timezone: string;
  userAgent: string;
  language: string;
  platform: string;
  cookieEnabled: boolean;
  javaEnabled: boolean;
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
    const getBrowserInfo = (): string => {
      const userAgent = navigator.userAgent;
      
      if (userAgent.includes("Chrome") && !userAgent.includes("Edg")) {
        const version = userAgent.match(/Chrome\/(\d+)/)?.[1] || "Unknown";
        return `Chrome ${version}`;
      } else if (userAgent.includes("Firefox")) {
        const version = userAgent.match(/Firefox\/(\d+)/)?.[1] || "Unknown";
        return `Firefox ${version}`;
      } else if (userAgent.includes("Safari") && !userAgent.includes("Chrome")) {
        const version = userAgent.match(/Version\/(\d+)/)?.[1] || "Unknown";
        return `Safari ${version}`;
      } else if (userAgent.includes("Edg")) {
        const version = userAgent.match(/Edg\/(\d+)/)?.[1] || "Unknown";
        return `Edge ${version}`;
      }
      
      return "Unknown Browser";
    };

    const getOSInfo = (): string => {
      const userAgent = navigator.userAgent;
      
      if (userAgent.includes("Windows NT")) {
        const version = userAgent.match(/Windows NT (\d+\.\d+)/)?.[1];
        const windowsVersions: { [key: string]: string } = {
          "10.0": "Windows 10/11",
          "6.3": "Windows 8.1",
          "6.2": "Windows 8",
          "6.1": "Windows 7",
        };
        return windowsVersions[version || ""] || "Windows";
      } else if (userAgent.includes("Mac OS X")) {
        const version = userAgent.match(/Mac OS X (\d+_\d+)/)?.[1]?.replace(/_/g, ".");
        return `macOS ${version || ""}`;
      } else if (userAgent.includes("Linux")) {
        return "Linux";
      } else if (userAgent.includes("Android")) {
        const version = userAgent.match(/Android (\d+\.\d+)/)?.[1];
        return `Android ${version || ""}`;
      } else if (userAgent.includes("iPhone") || userAgent.includes("iPad")) {
        const version = userAgent.match(/OS (\d+_\d+)/)?.[1]?.replace(/_/g, ".");
        return `iOS ${version || ""}`;
      }
      
      return "Unknown OS";
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

    const info: DeviceInfo = {
      browser: getBrowserInfo(),
      os: getOSInfo(),
      screen: getScreenInfo(),
      timezone: getTimezone(),
      userAgent: navigator.userAgent,
      language: navigator.language || "en-US",
      platform: navigator.platform || "Unknown",
      cookieEnabled: navigator.cookieEnabled,
      javaEnabled: checkJavaEnabled(),
    };

    setDeviceInfo(info);
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
