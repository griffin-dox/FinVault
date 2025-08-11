// Environment configuration
export const config = {
  // API Configuration
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || "https://finvault-g6r7.onrender.com",
    timeout: 30000, // 30 seconds
    retryAttempts: 3,
  },
  
  // App Configuration
  app: {
    name: "FinVault",
    version: "1.0.0",
    environment: import.meta.env.MODE,
    isDevelopment: import.meta.env.DEV,
    isProduction: import.meta.env.PROD,
  },
  
  // Feature Flags
  features: {
    enableAnalytics: import.meta.env.VITE_ENABLE_ANALYTICS === "true",
    enableDebugMode: import.meta.env.VITE_DEBUG_MODE === "true",
    enableErrorReporting: import.meta.env.VITE_ENABLE_ERROR_REPORTING === "true",
  },
  
  // Security
  security: {
    sessionTimeout: 30 * 60 * 1000, // 30 minutes
    maxLoginAttempts: 5,
    lockoutDuration: 15 * 60 * 1000, // 15 minutes
  },
  
  // Performance
  performance: {
    queryStaleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000, // 10 minutes
    debounceDelay: 300, // 300ms
  },
} as const;

// Type-safe config access
export type Config = typeof config; 