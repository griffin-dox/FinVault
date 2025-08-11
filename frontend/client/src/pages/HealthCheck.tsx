import React from 'react';
import { HealthStatus } from '../components/HealthStatus';
import { useHealthCheck } from '../hooks/useHealthCheck';
import { AlertTriangle, Info, Clock, RefreshCw } from 'lucide-react';

const HealthCheckPage: React.FC = () => {
  const { healthStatus, checkHealthNow, isLoading, isAnyServiceDown, getDownServices } = useHealthCheck();

  const getTroubleshootingTips = () => {
    const downServices = getDownServices();
    const tips = [];

    if (downServices.includes('Backend API')) {
      tips.push({
        service: 'Backend API',
        issue: 'Backend service is down (15-minute timeout on free plan)',
        solution: 'Wait for the service to wake up or trigger a request to wake it up',
        estimatedTime: '1-2 minutes after first request'
      });
    }

    if (downServices.includes('PostgreSQL')) {
      tips.push({
        service: 'PostgreSQL',
        issue: 'Database connection failed',
        solution: 'Check database credentials and connection string',
        estimatedTime: 'Immediate after fix'
      });
    }

    if (downServices.includes('MongoDB')) {
      tips.push({
        service: 'MongoDB',
        issue: 'MongoDB connection failed',
        solution: 'Check MongoDB URI and network connectivity',
        estimatedTime: 'Immediate after fix'
      });
    }



    return tips;
  };

  const formatUptime = (date: Date | null) => {
    if (!date) return 'Unknown';
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">System Health Monitor</h1>
          <p className="text-gray-600">
            Monitor the health of your FinVault backend services and databases
          </p>
        </div>

        {/* Status Overview */}
        <div className="mb-8">
          <HealthStatus showDetails={true} />
        </div>

        {/* Auto-refresh Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
            <div>
              <h3 className="font-medium text-blue-900 mb-1">Auto-refresh Active</h3>
              <p className="text-blue-700 text-sm">
                Health checks are performed automatically every 30 seconds. 
                The system monitors backend API (15-min timeout), PostgreSQL, and MongoDB connections.
              </p>
            </div>
          </div>
        </div>

        {/* Troubleshooting Section */}
        {isAnyServiceDown() && (
          <div className="bg-white rounded-lg border shadow-sm p-6 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-red-600" />
              <h2 className="text-xl font-semibold text-gray-900">Troubleshooting Guide</h2>
            </div>
            
            <div className="space-y-4">
              {getTroubleshootingTips().map((tip, index) => (
                <div key={index} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-gray-900">{tip.service}</h3>
                    <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      ~{tip.estimatedTime}
                    </span>
                  </div>
                  <p className="text-gray-700 mb-2">{tip.issue}</p>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Solution:</span> {tip.solution}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Service Details */}
        <div className="bg-white rounded-lg border shadow-sm p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Service Details</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="font-medium text-gray-900 mb-3">Backend API</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>Status:</span>
                  <span className={`font-medium ${
                    healthStatus.backend === 'healthy' ? 'text-green-600' : 
                    healthStatus.backend === 'unhealthy' ? 'text-red-600' : 'text-yellow-600'
                  }`}>
                    {healthStatus.backend}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>URL:</span>
                  <span className="font-mono text-xs">finvault-g6r7.onrender.com</span>
                </div>
                <div className="flex justify-between">
                  <span>Timeout:</span>
                  <span>15 minutes (free plan)</span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-medium text-gray-900 mb-3">Databases</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <div className="flex justify-between">
                  <span>PostgreSQL:</span>
                  <span className={`font-medium ${
                    healthStatus.postgresql === 'healthy' ? 'text-green-600' : 
                    healthStatus.postgresql === 'unhealthy' ? 'text-red-600' : 'text-yellow-600'
                  }`}>
                    {healthStatus.postgresql}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>MongoDB:</span>
                  <span className={`font-medium ${
                    healthStatus.mongodb === 'healthy' ? 'text-green-600' : 
                    healthStatus.mongodb === 'unhealthy' ? 'text-red-600' : 'text-yellow-600'
                  }`}>
                    {healthStatus.mongodb}
                  </span>
                </div>
                {/* Redis status fully removed */}
              </div>
            </div>
          </div>

          {/* Last Check Info */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm text-gray-500">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>Last checked: {healthStatus.lastChecked ? healthStatus.lastChecked.toLocaleString() : 'Never'}</span>
              </div>
              <button
                onClick={checkHealthNow}
                disabled={isLoading}
                className="flex items-center gap-2 px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                Refresh Now
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HealthCheckPage;