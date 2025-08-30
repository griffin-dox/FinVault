import { apiRequest } from "./queryClient";
import type { 
  RegisterInput, 
  LoginInput, 
  TransferInput, 
  User, 
  Transaction, 
  FraudAlert 
} from "@shared/schema";
import { COUNTRIES } from "@/lib/constants";

// Authentication API
export const authApi = {
  register: async (data: RegisterInput): Promise<{ user: Pick<User, 'id' | 'email'> }> => {
    const response = await apiRequest("POST", "/api/auth/register", data);
    return await response.json();
  },

  login: async (data: LoginInput): Promise<{ user: User }> => {
    const response = await apiRequest("POST", "/api/auth/login", data);
    return await response.json();
  },

  verifyEmail: async (email: string): Promise<{ message: string }> => {
    const response = await apiRequest("POST", "/api/auth/verify-email", { email });
    return await response.json();
  },

  completeOnboarding: async (data: {
    email: string;
    deviceFingerprint: any;
    behaviorProfile: any;
  }): Promise<{ user: User }> => {
    const response = await apiRequest("POST", "/api/auth/complete-onboarding", data);
    return await response.json();
  },
};

// User API
export const userApi = {
  getUsers: async (): Promise<{ users: User[] }> => {
    const response = await apiRequest("GET", "/api/users");
    return await response.json();
  },

  getUser: async (id: string): Promise<{ user: User }> => {
    const response = await apiRequest("GET", `/api/users/${id}`);
    return await response.json();
  },

  updateUser: async (id: string, updates: Partial<User>): Promise<{ user: User }> => {
    const response = await apiRequest("PUT", `/api/admin/users/${id}`, updates);
    return await response.json();
  },
};

// Transaction API
export const transactionApi = {
  getTransactions: async (userId?: string): Promise<{ transactions: Transaction[] }> => {
    const url = userId ? `/api/transactions?userId=${userId}` : "/api/transactions";
    const response = await apiRequest("GET", url);
    return await response.json();
  },

  createTransaction: async (data: TransferInput & { userId: string }): Promise<{ 
    transaction: Transaction; 
    riskScore: number; 
  }> => {
    const response = await apiRequest("POST", "/api/transactions", data);
    return await response.json();
  },

  updateTransaction: async (id: string, updates: { status: string }): Promise<{ transaction: Transaction }> => {
    const response = await apiRequest("PUT", `/api/admin/transactions/${id}`, updates);
    return await response.json();
  },
};

// Fraud Alert API
export const fraudApi = {
  getFraudAlerts: async (): Promise<{ alerts: FraudAlert[] }> => {
    const response = await apiRequest("GET", "/api/fraud-alerts");
    return await response.json();
  },
};

// Admin API
export const adminApi = {
  updateUserRisk: async (userId: string, riskLevel: string): Promise<{ user: User }> => {
    const response = await apiRequest("PUT", `/api/admin/users/${userId}`, { riskLevel });
    return await response.json();
  },

  updateTransactionStatus: async (transactionId: string, status: string): Promise<{ transaction: Transaction }> => {
    const response = await apiRequest("PUT", `/api/admin/transactions/${transactionId}`, { status });
    return await response.json();
  },
};

// Utility functions for API data formatting
export const apiUtils = {
  formatAmount: (amount: number): string => {
    return amount.toLocaleString('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2,
    });
  },

  formatDate: (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      timeZone: 'Asia/Kolkata',
    });
  },

  formatDateTime: (dateString: string): { date: string; time: string } => {
    const date = new Date(dateString);
    return {
      date: date.toLocaleDateString('en-IN', {
        month: 'short', 
        day: 'numeric', 
        year: 'numeric',
        timeZone: 'Asia/Kolkata',
      }),
      time: date.toLocaleTimeString('en-IN', {
        hour: 'numeric', 
        minute: '2-digit', 
        hour12: true,
        timeZone: 'Asia/Kolkata',
      }),
    };
  },

  getRiskLevel: (riskScore: number): 'low' | 'medium' | 'high' => {
    if (riskScore <= 30) return 'low';
    if (riskScore <= 60) return 'medium';
    return 'high';
  },

  getRiskColor: (riskScore: number): string => {
    if (riskScore <= 30) return 'text-green-600';
    if (riskScore <= 60) return 'text-yellow-600';  
    return 'text-red-600';
  },

  getRiskBadgeVariant: (riskScore: number): 'default' | 'secondary' | 'destructive' => {
    if (riskScore <= 30) return 'default';
    if (riskScore <= 60) return 'secondary';
    return 'destructive';
  },
};

export function formatAmountByCountry(amount: number, countryCode: string): string {
  try {
    const numAmount = typeof amount === 'number' && !isNaN(amount) ? amount : 0;
    const code = typeof countryCode === 'string' ? countryCode : 'IN';
    const country = COUNTRIES.find(c => c.code === code);
    if (!country) {
      // fallback to INR
      return numAmount.toLocaleString('en-IN', { style: 'currency', currency: 'INR' });
    }
    return numAmount.toLocaleString(country.locale, { style: 'currency', currency: country.currency });
  } catch {
    return '$0.00';
  }
}
