// Application Constants
export const APP_NAME = "SecureBank";
export const APP_VERSION = "1.0.0";

// API Configuration
export const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? '/api' 
  : '/api';

// Authentication
export const AUTH_TOKEN_KEY = "securebank_user";
export const PENDING_EMAIL_KEY = "securebank_pending_email";

// Risk Levels
export const RISK_LEVELS = {
  LOW: { value: 'low', label: 'Low', threshold: 30, color: 'green' },
  MEDIUM: { value: 'medium', label: 'Medium', threshold: 60, color: 'yellow' },
  HIGH: { value: 'high', label: 'High', threshold: 100, color: 'red' },
} as const;

// Transaction Types
export const TRANSACTION_TYPES = {
  DEPOSIT: { value: 'deposit', label: 'Deposit', icon: 'arrow-down-left' },
  TRANSFER: { value: 'transfer', label: 'Transfer', icon: 'arrow-up-right' },
  WITHDRAWAL: { value: 'withdrawal', label: 'Withdrawal', icon: 'arrow-up-right' },
} as const;

// Transaction Status
export const TRANSACTION_STATUS = {
  COMPLETED: { value: 'completed', label: 'Completed', variant: 'default' },
  PENDING: { value: 'pending', label: 'Pending', variant: 'secondary' },
  BLOCKED: { value: 'blocked', label: 'Blocked', variant: 'destructive' },
} as const;

// Countries for registration
export const COUNTRIES = [
  { code: 'IN', name: 'India', currency: 'INR', locale: 'en-IN', symbol: '₹' },
  { code: 'US', name: 'United States', currency: 'USD', locale: 'en-US', symbol: '$' },
  { code: 'UK', name: 'United Kingdom', currency: 'GBP', locale: 'en-GB', symbol: '£' },
  { code: 'CA', name: 'Canada', currency: 'CAD', locale: 'en-CA', symbol: 'CA$' },
  { code: 'DE', name: 'Germany', currency: 'EUR', locale: 'de-DE', symbol: '€' },
  { code: 'FR', name: 'France', currency: 'EUR', locale: 'fr-FR', symbol: '€' },
  { code: 'AU', name: 'Australia', currency: 'AUD', locale: 'en-AU', symbol: 'A$' },
  { code: 'JP', name: 'Japan', currency: 'JPY', locale: 'ja-JP', symbol: '¥' },
  { code: 'BR', name: 'Brazil', currency: 'BRL', locale: 'pt-BR', symbol: 'R$' },
  { code: 'CN', name: 'China', currency: 'CNY', locale: 'zh-CN', symbol: '¥' },
] as const;

// Onboarding Steps
export const ONBOARDING_STEPS = {
  REGISTER: { step: 1, path: '/register', title: 'Create Account' },
  VERIFY: { step: 2, path: '/verify-email', title: 'Verify Email' },
  ONBOARD: { step: 3, path: '/onboarding', title: 'Security Setup' },
} as const;

// Navigation Links
export const NAV_LINKS = {
  PUBLIC: [
    { href: '/', label: 'Home' },
  ],
  AUTHENTICATED: [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/transactions', label: 'Transactions' },
  ],
  ADMIN: [
    { href: '/admin', label: 'Admin' },
  ],
} as const;

// Admin Configuration
export const ADMIN_CONFIG = {
  DEFAULT_RISK_THRESHOLD: 75,
  DEFAULT_AUTO_BLOCK_THRESHOLD: 90,
  FRAUD_ALERT_REFRESH_INTERVAL: 30000, // 30 seconds
  TRANSACTION_REFRESH_INTERVAL: 60000, // 1 minute
} as const;

// Behavioral Analysis
export const BEHAVIOR_CONFIG = {
  MIN_TYPING_COMPLETION: 0.8, // 80% of target text
  KEYSTROKE_VARIANCE_THRESHOLD: 10000,
  FAST_TYPING_THRESHOLD: 100, // ms
  SLOW_TYPING_THRESHOLD: 300, // ms
  MIN_KEYSTROKES_FOR_ANALYSIS: 5,
} as const;

// UI Constants
export const UI_CONFIG = {
  TOAST_DURATION: 5000,
  MODAL_ANIMATION_DURATION: 300,
  PAGE_TRANSITION_DURATION: 500,
  MOBILE_BREAKPOINT: 768,
} as const;

// Security Configuration
export const SECURITY_CONFIG = {
  MIN_PASSWORD_LENGTH: 8,
  SESSION_TIMEOUT: 3600000, // 1 hour in milliseconds
  MAX_LOGIN_ATTEMPTS: 5,
  DEVICE_FINGERPRINT_VERSION: '1.0',
} as const;

// Banking Demo Data (for display purposes only)
export const DEMO_BALANCES = {
  CHECKING: 12847.92,
  SAVINGS: 45392.14,
  TOTAL: 58240.06,
  AVAILABLE_CREDIT: 15000.00,
  MONTHLY_SPENDING: 2847.32,
} as const;

// Validation Messages
export const VALIDATION_MESSAGES = {
  REQUIRED_FIELD: "This field is required",
  INVALID_EMAIL: "Please enter a valid email address",
  INVALID_PHONE: "Please enter a valid phone number",
  MIN_LENGTH: (min: number) => `Must be at least ${min} characters`,
  MAX_LENGTH: (max: number) => `Must be no more than ${max} characters`,
  INVALID_AMOUNT: "Please enter a valid amount",
  TERMS_REQUIRED: "You must agree to the terms and conditions",
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  GENERIC: "Something went wrong. Please try again.",
  NETWORK: "Network error. Please check your connection.",
  UNAUTHORIZED: "You are not authorized to perform this action.",
  NOT_FOUND: "The requested resource was not found.",
  VALIDATION: "Please check your input and try again.",
  SERVER: "Server error. Please try again later.",
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  REGISTRATION: "Account created successfully!",
  LOGIN: "Welcome back!",
  EMAIL_VERIFIED: "Email verified successfully!",
  ONBOARDING_COMPLETE: "Security profile created successfully!",
  TRANSFER_SENT: "Transfer completed successfully!",
  SETTINGS_SAVED: "Settings saved successfully!",
} as const;

// Feature Flags (for development/testing)
export const FEATURE_FLAGS = {
  ENABLE_LOCATION_TRACKING: true,
  ENABLE_BEHAVIORAL_ANALYSIS: true,
  ENABLE_FRAUD_DETECTION: true,
  ENABLE_ADMIN_PANEL: true,
  ENABLE_DEMO_MODE: process.env.NODE_ENV === 'development',
} as const;

// Type exports for better TypeScript support
export type RiskLevel = keyof typeof RISK_LEVELS;
export type TransactionType = keyof typeof TRANSACTION_TYPES;
export type TransactionStatus = keyof typeof TRANSACTION_STATUS;
export type OnboardingStep = keyof typeof ONBOARDING_STEPS;
