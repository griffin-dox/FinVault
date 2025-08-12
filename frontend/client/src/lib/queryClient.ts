import { QueryClient, QueryFunction } from "@tanstack/react-query";

// Two-mode config: local vs prod, plus optional runtime override
const LOCAL_API_BASE_URL = "http://127.0.0.1:8000"; // default loopback; we'll auto-fallback to localhost if needed
const PROD_API_BASE_URL = "https://finvault-g6r7.onrender.com"; // e.g., "https://api.example.com" (leave empty to use same-origin)

// Environment flags (baked by Vite)
const isDevelopment = import.meta.env.DEV;
const isProduction = import.meta.env.PROD;

// Optional runtime override for static hosting without rebuilds
const RUNTIME_BASE = typeof window !== "undefined" ? (window as any).__API_BASE_URL__ as string | undefined : undefined;
const CHOSEN_BASE = RUNTIME_BASE || (isDevelopment ? LOCAL_API_BASE_URL : PROD_API_BASE_URL);
const DEFAULT_BASE = typeof window !== "undefined" ? window.location.origin : "";
const API_BASE_URL = (CHOSEN_BASE || DEFAULT_BASE).replace(/\/$/, "");

// Environment-based configuration (kept for logs/backoff)

function buildApiUrl(path: string) {
  if (!path.startsWith("/")) path = "/" + path;
  // If API_BASE_URL is empty, return relative path (use dev proxy)
  return `${API_BASE_URL}${path}`;
}

// Build a URL using the swapped loopback host (localhost <-> 127.0.0.1)
function buildFallbackApiUrl(path: string) {
  if (!path.startsWith("/")) path = "/" + path;
  try {
    const u = new URL(`${API_BASE_URL}${path}`);
    if (u.hostname === "localhost") u.hostname = "127.0.0.1";
    else if (u.hostname === "127.0.0.1") u.hostname = "localhost";
    return u.toString();
  } catch {
    return `${API_BASE_URL}${path}`;
  }
}

function isLoopbackHost(hostname: string) {
  return hostname === "localhost" || hostname === "127.0.0.1";
}

function swapLoopbackInUrl(urlStr: string): string {
  try {
    const u = new URL(urlStr);
    if (!isLoopbackHost(u.hostname)) return urlStr;
    u.hostname = u.hostname === "localhost" ? "127.0.0.1" : "localhost";
    return u.toString();
  } catch {
    return urlStr;
  }
}

// Fetch with automatic localhost <-> 127.0.0.1 fallback on network errors
async function fetchWithLocalFallback(input: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (err: any) {
    // Only fallback on network-level failures
    const isNetworkError = err instanceof TypeError && String(err.message || "").toLowerCase().includes("fetch");
    if (!isNetworkError) throw err;
    // Try swapped loopback host if applicable
    const swapped = swapLoopbackInUrl(input);
    if (swapped !== input) {
      return await fetch(swapped, init);
    }
    throw err;
  }
}

function getStoredToken(): string | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    const t = localStorage.getItem("securebank_token");
    return t || undefined;
  } catch {
    return undefined;
  }
}

// Read CSRF token from cookie (double-submit pattern)
function getCsrfToken(): string | undefined {
  if (typeof document === "undefined") return undefined;
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (const part of cookies) {
    const [rawKey, ...rest] = part.trim().split("=");
    const key = decodeURIComponent(rawKey || "");
    if (key === "csrf_token") {
      return decodeURIComponent(rest.join("=") || "");
    }
  }
  return undefined;
}

// Get or acquire a CSRF token cross-site: if cookie isn't readable on this origin,
// fetch it from the backend helper endpoint and return the token (also sets cookie on API origin).
async function ensureCsrfToken(fetchBase: (path: string) => string): Promise<string | undefined> {
  const existing = getCsrfToken();
  if (existing) return existing;
  try {
  const url = fetchBase("/csrf-token");
  const res = await fetchWithLocalFallback(url, {
      method: "GET",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    if (!res.ok) return undefined;
    // Prefer header value if provided, fallback to JSON body
    const headerToken = res.headers.get("X-CSRF-Token") || res.headers.get("x-csrf-token");
    if (headerToken) return headerToken;
    try {
      const data = (await res.json()) as { csrf?: string };
      return data?.csrf;
    } catch {
      return undefined;
    }
  } catch {
    return undefined;
  }
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
  // Attach CSRF header for unsafe methods when cookie auth is present
  const isUnsafe = ["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase());
  let csrf = isUnsafe ? getCsrfToken() : undefined;
  if (isUnsafe && !csrf) {
    csrf = await ensureCsrfToken(buildApiUrl);
  }
  
  try {
  const res = await fetchWithLocalFallback(buildApiUrl(url), {
      method,
      headers: {
        ...(data ? { "Content-Type": "application/json" } : {}),
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
  ...(getStoredToken() ? { Authorization: `Bearer ${getStoredToken()}` } : {}),
  ...(csrf ? { "X-CSRF-Token": csrf } : {}),
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
  const res = await fetchWithLocalFallback(url, {
      credentials: "include",
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
  ...(getStoredToken() ? { Authorization: `Bearer ${getStoredToken()}` } : {}),
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
