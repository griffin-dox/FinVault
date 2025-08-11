import React from 'react';
import { useHealthCheck } from '../hooks/useHealthCheck';
import { RefreshCw, AlertTriangle, CheckCircle, XCircle, Clock } from 'lucide-react';

interface HealthStatusProps {
  showDetails?: boolean;
  compact?: boolean;
  className?: string;
}

export const HealthStatus: React.FC<HealthStatusProps> = ({ 
  showDetails = true, 
  compact = false,
  className = '' 
}) => {
  const {
    healthStatus,
    isLoading,
    checkHealthNow,
    isAnyServiceDown,
    getDownServices,
    getStatusColor,
    getStatusIcon,
  } = useHealthCheck();

  const formatLastChecked = (date: Date | null) => {
    if (!date) return 'Never';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const seconds = Math.floor((diff % 60000) / 1000);
    
    if (minutes > 0) {
      return `${minutes}m ${seconds}s ago`;
    }
    return `${seconds}s ago`;
  };

  const getStatusIconComponent = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'unhealthy':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'checking':
        return <RefreshCw className="w-4 h-4 text-yellow-600 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-600" />;
    }
  };

  if (compact) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="flex items-center gap-1">
          {isAnyServiceDown() ? (
            <AlertTriangle className="w-4 h-4 text-red-600" />
          ) : (
            <CheckCircle className="w-4 h-4 text-green-600" />
          )}
          <span className={`text-sm font-medium ${isAnyServiceDown() ? 'text-red-600' : 'text-green-600'}`}>
            {isAnyServiceDown() ? 'Services Down' : 'All Healthy'}
          </span>
        </div>
        <button
          onClick={checkHealthNow}
          disabled={isLoading}
          className="p-1 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
          title="Check health now"
        >
          <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border shadow-sm p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">System Health</h3>
        <button
          onClick={checkHealthNow}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1 text-sm bg-blue-50 text-blue-700 rounded-md hover:bg-blue-100 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Check Now
        </button>
      </div>

      {showDetails && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
              <div className="flex items-center gap-2">
                {getStatusIconComponent(healthStatus.backend)}
                <span className="font-medium">Backend API</span>
              </div>
              <span className={`ml-auto text-sm ${getStatusColor(healthStatus.backend)}`}>
                {healthStatus.backend}
              </span>
            </div>

            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
              <div className="flex items-center gap-2">
                {getStatusIconComponent(healthStatus.postgresql)}
                <span className="font-medium">PostgreSQL</span>
              </div>
              <span className={`ml-auto text-sm ${getStatusColor(healthStatus.postgresql)}`}>
                {healthStatus.postgresql}
              </span>
            </div>

            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
              <div className="flex items-center gap-2">
                {getStatusIconComponent(healthStatus.mongodb)}
                <span className="font-medium">MongoDB</span>
              </div>
              <span className={`ml-auto text-sm ${getStatusColor(healthStatus.mongodb)}`}>
                {healthStatus.mongodb}
              </span>
            </div>

            <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md">
              <div className="flex items-center gap-2">
                {getStatusIconComponent(healthStatus.redis)}
                <span className="font-medium">Redis</span>
              </div>
              <span className={`ml-auto text-sm ${getStatusColor(healthStatus.redis)}`}>
                {healthStatus.redis}
              </span>
            </div>
          </div>

          {isAnyServiceDown() && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <div className="flex items-center gap-2 text-red-800">
                <AlertTriangle className="w-4 h-4" />
                <span className="font-medium">Services Down:</span>
              </div>
              <ul className="mt-2 ml-6 text-sm text-red-700 list-disc">
                {getDownServices().map((service) => (
                  <li key={service}>{service}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="text-xs text-gray-500 text-center">
            Last checked: {formatLastChecked(healthStatus.lastChecked)}
          </div>
        </div>
      )}

      {!showDetails && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isAnyServiceDown() ? (
              <AlertTriangle className="w-4 h-4 text-red-600" />
            ) : (
              <CheckCircle className="w-4 h-4 text-green-600" />
            )}
            <span className={`font-medium ${isAnyServiceDown() ? 'text-red-600' : 'text-green-600'}`}>
              {isAnyServiceDown() ? 'Some services are down' : 'All systems operational'}
            </span>
          </div>
          <span className="text-xs text-gray-500">
            {formatLastChecked(healthStatus.lastChecked)}
          </span>
        </div>
      )}
    </div>
  );
}; 