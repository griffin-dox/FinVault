import React, { useState } from 'react';
import { useHealthCheck } from '../hooks/useHealthCheck';
import { HealthStatus } from './HealthStatus';
import { Activity, AlertTriangle, CheckCircle } from 'lucide-react';

interface HealthIndicatorProps {
  showDetailsOnClick?: boolean;
  className?: string;
}

export const HealthIndicator: React.FC<HealthIndicatorProps> = ({ 
  showDetailsOnClick = true,
  className = '' 
}) => {
  const { healthStatus, isAnyServiceDown } = useHealthCheck();
  const [showDetails, setShowDetails] = useState(false);

  const getStatusColor = () => {
    if (isAnyServiceDown()) {
      return 'text-red-600 bg-red-50 hover:bg-red-100';
    }
    return 'text-green-600 bg-green-50 hover:bg-green-100';
  };

  const getStatusIcon = () => {
    if (isAnyServiceDown()) {
      return <AlertTriangle className="w-4 h-4" />;
    }
    return <CheckCircle className="w-4 h-4" />;
  };

  const getStatusText = () => {
    if (isAnyServiceDown()) {
      return 'Services Down';
    }
    return 'All Healthy';
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => showDetailsOnClick && setShowDetails(!showDetails)}
        className={`flex items-center gap-2 px-3 py-2 rounded-md transition-colors ${getStatusColor()}`}
        title={showDetailsOnClick ? 'Click to view details' : getStatusText()}
      >
        <Activity className="w-4 h-4" />
        <span className="text-sm font-medium">{getStatusText()}</span>
        {showDetailsOnClick && (
          <span className="text-xs opacity-75">
            {healthStatus.lastChecked ? 
              `${Math.floor((Date.now() - healthStatus.lastChecked.getTime()) / 60000)}m ago` : 
              'Never'
            }
          </span>
        )}
      </button>

      {/* Dropdown with details */}
      {showDetails && showDetailsOnClick && (
        <div className="absolute top-full right-0 mt-2 w-80 z-50">
          <HealthStatus showDetails={true} />
        </div>
      )}
    </div>
  );
}; 