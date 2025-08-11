export interface HealthStatus {
  backend: 'healthy' | 'unhealthy' | 'checking' | 'unknown';
  postgresql: 'healthy' | 'unhealthy' | 'checking' | 'unknown';
  mongodb: 'healthy' | 'unhealthy' | 'checking' | 'unknown';
  redis: 'healthy' | 'unhealthy' | 'checking' | 'unknown';
  lastChecked: Date | null;
  isAllHealthy: boolean;
}

export interface HealthResponse {
  status: string;
  postgres: string;
  mongodb: string;
  redis: string;
}

class HealthCheckService {
  private backendUrl: string;
  private checkInterval: number = 30000; // 30 seconds
  private intervalId: NodeJS.Timeout | null = null;
  private listeners: ((status: HealthStatus) => void)[] = [];
  private currentStatus: HealthStatus = {
    backend: 'unknown',
    postgresql: 'unknown',
    mongodb: 'unknown',
    redis: 'unknown',
    lastChecked: null,
    isAllHealthy: false
  };

  constructor() {
    // Use environment variable or default to your Render backend URL
    this.backendUrl = import.meta.env.VITE_API_URL || 'https://finvault-g6r7.onrender.com';
  }

  // Start periodic health checks
  startPeriodicChecks(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    
    // Perform initial check
    this.performHealthCheck();
    
    // Set up periodic checks
    this.intervalId = setInterval(() => {
      this.performHealthCheck();
    }, this.checkInterval);
  }

  // Stop periodic health checks
  stopPeriodicChecks(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  // Perform a single health check
  async performHealthCheck(): Promise<HealthStatus> {
    // Update status to checking
    this.updateStatus({
      ...this.currentStatus,
      backend: 'checking',
      postgresql: 'checking',
      mongodb: 'checking',
      lastChecked: new Date()
    });

    try {
      // Check backend health endpoint
      const response = await fetch(`${this.backendUrl}/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        // 10 second timeout for backend check
        signal: AbortSignal.timeout(10000)
      });

      if (response.ok) {
        const healthData: HealthResponse = await response.json();
        
        const newStatus: HealthStatus = {
          backend: 'healthy',
          postgresql: healthData.postgres === 'connected' ? 'healthy' : 'unhealthy',
          mongodb: healthData.mongodb === 'connected' ? 'healthy' : 'unhealthy',
          redis: healthData.redis === 'connected' ? 'healthy' : 'unhealthy',
          lastChecked: new Date(),
          isAllHealthy: healthData.status === 'ok' && 
                       healthData.postgres === 'connected' && 
                       healthData.mongodb === 'connected'
        };

        this.updateStatus(newStatus);
        return newStatus;
      } else {
        throw new Error(`Backend responded with status: ${response.status}`);
      }
    } catch (error) {
      console.error('Health check failed:', error);
      
      const newStatus: HealthStatus = {
        backend: 'unhealthy',
        postgresql: 'unknown',
        mongodb: 'unknown',
        redis: 'unknown',
        lastChecked: new Date(),
        isAllHealthy: false
      };

      this.updateStatus(newStatus);
      return newStatus;
    }
  }

  // Get current health status
  getCurrentStatus(): HealthStatus {
    return { ...this.currentStatus };
  }

  // Subscribe to health status changes
  subscribe(listener: (status: HealthStatus) => void): () => void {
    this.listeners.push(listener);
    
    // Return unsubscribe function
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }

  // Update status and notify listeners
  private updateStatus(status: HealthStatus): void {
    this.currentStatus = status;
    this.listeners.forEach(listener => listener(status));
  }

  // Manual health check (for immediate status)
  async checkHealthNow(): Promise<HealthStatus> {
    return await this.performHealthCheck();
  }

  // Check if any service is down
  isAnyServiceDown(): boolean {
    return !this.currentStatus.isAllHealthy;
  }

  // Get services that are down
  getDownServices(): string[] {
    const downServices: string[] = [];
    
    if (this.currentStatus.backend === 'unhealthy') downServices.push('Backend API');
    if (this.currentStatus.postgresql === 'unhealthy') downServices.push('PostgreSQL');
    if (this.currentStatus.mongodb === 'unhealthy') downServices.push('MongoDB');
    
    return downServices;
  }
}

// Create singleton instance
export const healthCheckService = new HealthCheckService(); 