import { useState, useEffect, useCallback } from 'react';
import { healthCheckService, HealthStatus } from '../lib/healthCheck';

export const useHealthCheck = () => {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>(healthCheckService.getCurrentStatus());
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Subscribe to health status changes
    const unsubscribe = healthCheckService.subscribe((status) => {
      setHealthStatus(status);
    });

    // Start periodic health checks
    healthCheckService.startPeriodicChecks();

    // Cleanup on unmount
    return () => {
      unsubscribe();
      healthCheckService.stopPeriodicChecks();
    };
  }, []);

  // Manual health check function
  const checkHealthNow = useCallback(async () => {
    setIsLoading(true);
    try {
      await healthCheckService.checkHealthNow();
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Check if any service is down
  const isAnyServiceDown = useCallback(() => {
    return healthCheckService.isAnyServiceDown();
  }, [healthStatus]);

  // Get services that are down
  const getDownServices = useCallback(() => {
    return healthCheckService.getDownServices();
  }, [healthStatus]);

  // Get status color for UI
  const getStatusColor = (status: HealthStatus['backend' | 'postgresql' | 'mongodb' | 'redis']) => {
    switch (status) {
      case 'healthy':
        return 'text-green-600';
      case 'unhealthy':
        return 'text-red-600';
      case 'checking':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  // Get status icon for UI
  const getStatusIcon = (status: HealthStatus['backend' | 'postgresql' | 'mongodb' | 'redis']) => {
    switch (status) {
      case 'healthy':
        return '✓';
      case 'unhealthy':
        return '✗';
      case 'checking':
        return '⟳';
      default:
        return '?';
    }
  };

  return {
    healthStatus,
    isLoading,
    checkHealthNow,
    isAnyServiceDown,
    getDownServices,
    getStatusColor,
    getStatusIcon,
  };
}; 