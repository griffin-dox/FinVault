import { QueryClient, QueryFunction } from "@tanstack/react-query";

const API_BASE_URL = "https://finvault-g6r7.onrender.com";

// Environment-based configuration
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

function buildApiUrl(path: string) {
  if (!path.startsWith("/")) path = "/" + path;
  return `${API_BASE_URL.replace(/\/$/, "")}${path}`;
}

// Enhanced error handling
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function apiRequest(
  method: string,
  url: string,
  data?: unknown | undefined,
): Promise<Response> {
  const startTime = Date.now();
  
  try {
    const res = await fetch(buildApiUrl(url), {
      method,
      headers: {
        ...(data ? { "Content-Type": "application/json" } : {}),
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: data ? JSON.stringify(data) : undefined,
      credentials: "include",
    });

    const responseTime = Date.now() - startTime;
    
    // Log performance in development
    if (isDevelopment) {
      console.log(`[API] ${method} ${url} - ${res.status} (${responseTime}ms)`);
    }

    if (!res.ok) {
      let errorBody;
      try {
        errorBody = await res.json();
      } catch {
        errorBody = await res.text();
      }
      
      // Enhanced error handling
      const error = new ApiError(
        errorBody?.message || `HTTP ${res.status}: ${res.statusText}`,
        res.status,
        errorBody
      );
      
      // Log errors in development
      if (isDevelopment) {
        console.error(`[API Error] ${method} ${url}:`, error);
      }
      
      throw error;
    }
    
    return res;
  } catch (error) {
    // Network errors
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new ApiError('Network error - please check your connection', 0);
    }
    throw error;
  }
}

type UnauthorizedBehavior = "returnNull" | "throw";
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const url = buildApiUrl(queryKey.join("/"));
    const res = await fetch(url, {
      credentials: "include",
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    if (!res.ok) {
      let errorBody;
      try {
        errorBody = await res.json();
      } catch {
        errorBody = await res.text();
      }
      throw new ApiError(
        errorBody?.message || `HTTP ${res.status}: ${res.statusText}`,
        res.status,
        errorBody
      );
    }
    return await res.json();
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error) => {
        // Don't retry on 4xx errors (except 408, 429)
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return error.status === 408 || error.status === 429;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: (failureCount, error) => {
        // Don't retry mutations on 4xx errors
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    },
  },
});
