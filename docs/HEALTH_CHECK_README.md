# Health Check System

A comprehensive health monitoring system for FinVault that monitors backend API, PostgreSQL, MongoDB, and Redis services from the frontend.

## Features

- **Real-time Monitoring**: Automatic health checks every 30 seconds
- **Service Status**: Monitors Backend API, PostgreSQL, MongoDB, and Redis
- **Visual Indicators**: Color-coded status indicators (green/red/yellow)
- **Troubleshooting Guide**: Automatic suggestions when services are down
- **Multiple UI Components**: Compact indicator, detailed view, and dedicated page

## Components

### 1. HealthCheckService (`src/lib/healthCheck.ts`)
Core service that handles health check logic:
- Performs periodic health checks
- Manages service status
- Provides subscription system for real-time updates

### 2. useHealthCheck Hook (`src/hooks/useHealthCheck.ts`)
React hook that provides health check functionality:
- Manages component state
- Provides utility functions
- Handles cleanup on unmount

### 3. HealthStatus Component (`src/components/HealthStatus.tsx`)
Main health status display component:
- Shows detailed status of all services
- Provides manual refresh functionality
- Displays troubleshooting information

### 4. HealthIndicator Component (`src/components/HealthIndicator.tsx`)
Compact status indicator:
- Shows overall system health
- Can be embedded in navbar or dashboard
- Optional dropdown with detailed view

### 5. HealthCheckPage (`src/pages/HealthCheck.tsx`)
Dedicated health monitoring page:
- Comprehensive system overview
- Troubleshooting guide
- Service details and configuration info

## Usage

### Basic Health Check
```tsx
import { useHealthCheck } from '@/hooks/useHealthCheck';

function MyComponent() {
  const { healthStatus, isAnyServiceDown } = useHealthCheck();
  
  return (
    <div>
      {isAnyServiceDown() ? 'Services Down' : 'All Healthy'}
    </div>
  );
}
```

### Health Status Component
```tsx
import { HealthStatus } from '@/components/HealthStatus';

// Full details view
<HealthStatus showDetails={true} />

// Compact view
<HealthStatus showDetails={false} />
```

### Health Indicator in Navbar
```tsx
import { HealthIndicator } from '@/components/HealthIndicator';

// With dropdown details
<HealthIndicator showDetailsOnClick={true} />

// Simple indicator only
<HealthIndicator showDetailsOnClick={false} />
```

## Configuration

### Environment Variables
Create a `.env` file in the frontend/client directory:

```env
# Production API URL
VITE_API_URL=https://finvault-g6r7.onrender.com

# Development API URL (uncomment for local development)
# VITE_API_URL=http://localhost:8000
```

### Backend Health Endpoint
The system expects a `/health` endpoint on your backend that returns:

```json
{
  "status": "ok",
  "postgres": "connected",
  "mongodb": "connected", 
  "redis": "connected"
}
```

## Service Timeouts

### Render Free Plan Limitations
- **Backend API**: 15-minute timeout after inactivity
- **PostgreSQL**: ~1 week timeout after inactivity
- **MongoDB**: ~1 week timeout after inactivity
- **Redis**: ~1 week timeout after inactivity

### Health Check Intervals
- **Automatic checks**: Every 30 seconds
- **Manual refresh**: Available on demand
- **Timeout**: 10 seconds per health check request

## Troubleshooting

### Common Issues

1. **Backend API Down**
   - **Cause**: 15-minute timeout on Render free plan
   - **Solution**: Wait 1-2 minutes after first request
   - **Prevention**: Use health check to wake up service

2. **Database Connection Failed**
   - **Cause**: Database service timeout or configuration issue
   - **Solution**: Check connection strings and credentials
   - **Prevention**: Monitor health status regularly

3. **Health Check Not Working**
   - **Cause**: CORS issues or incorrect API URL
   - **Solution**: Verify API URL and CORS configuration
   - **Prevention**: Test health endpoint directly

### Manual Testing
Test the health endpoint directly:
```bash
curl https://finvault-g6r7.onrender.com/health
```

## Integration Points

### Navbar Integration
The health indicator is automatically added to the navbar for authenticated users.

### Route Integration
Access the health check page at `/health` in your application.

### Dashboard Integration
You can add the HealthStatus component to your dashboard for monitoring.

## Monitoring Strategy

### For Development
- Use local API URL for testing
- Monitor console for health check logs
- Test with services intentionally down

### For Production
- Monitor health status regularly
- Set up alerts for service downtime
- Use health check to wake up sleeping services

## Performance Considerations

- Health checks are lightweight (10-second timeout)
- Automatic cleanup prevents memory leaks
- Subscription system ensures efficient updates
- Minimal impact on application performance

## Security

- Health endpoint should be public (no authentication required)
- No sensitive information exposed in health checks
- CORS properly configured for cross-origin requests
- Rate limiting recommended for production

## Future Enhancements

- Email/SMS alerts for service downtime
- Historical health data and trends
- Service-specific health metrics
- Integration with monitoring services (UptimeRobot, etc.)
- Health check API for external monitoring 