# Admin Dashboard

## Overview

The FinVault admin dashboard provides comprehensive system monitoring, user management, and advanced analytics capabilities. It features interactive heatmaps for fraud detection and real-time system status monitoring.

## Features

### User Management

- **User Search & Filtering**: Search users by email, name, or ID
- **User Details**: View complete user profiles including verification status, risk levels, and activity history
- **Role Management**: Assign and modify user roles with RBAC controls
- **Bulk Operations**: Perform batch operations on multiple users

### Transaction Monitoring

- **Transaction Overview**: View all transactions with real-time status updates
- **Risk Assessment**: Monitor transaction risk scores and fraud indicators
- **Status Management**: Update transaction statuses and add admin notes
- **Audit Trail**: Complete audit logging for all admin actions

### Fraud Detection & Analytics

#### Heatmap Visualization

The admin dashboard includes three types of interactive heatmaps powered by Leaflet:

1. **Transaction Risk Heatmap** (`/admin/heatmap-data`)

   - Visualizes high-risk transaction locations
   - Color-coded by risk level (red = high risk, yellow = medium, green = low)
   - Shows transaction volume and patterns
   - Supports time-based filtering

2. **Login Activity Heatmap** (`/admin/login-heatmap`)

   - Displays authentication patterns across geographic locations
   - Highlights unusual login locations and times
   - Shows login success/failure rates by location
   - Helps identify potential account takeover attempts

3. **User Activity Heatmap** (`/admin/user-activity-heatmap`)
   - Tracks individual user behavior patterns
   - Shows user movement and activity clusters
   - Supports user-specific analysis
   - Useful for behavioral pattern recognition

#### Interactive Features

- **Zoom & Pan**: Navigate through different geographic regions
- **Time Filtering**: Filter data by date ranges and time periods
- **Location Clustering**: Groups nearby activities to reduce visual noise
- **Risk Overlay**: Toggle risk level overlays on map layers
- **Export Capabilities**: Export heatmap data for external analysis

### System Monitoring

- **Health Checks**: Real-time system health status
- **Performance Metrics**: API response times, database performance
- **Alert Management**: View and manage system alerts
- **Resource Usage**: Monitor server resources and capacity

### Risk Rule Management

- **Dynamic Risk Rules**: Adjust risk scoring parameters in real-time
- **Rule Testing**: Test rule changes before deployment
- **Audit Logging**: Track all rule modifications
- **Rollback Capabilities**: Quickly revert to previous rule sets

## API Endpoints

### User Management

```
GET /admin/users - List users with pagination and search
GET /admin/users/{user_id} - Get detailed user information
PUT /admin/users/{user_id}/role - Update user role
```

### Transaction Management

```
GET /admin/transactions - List all transactions
PUT /admin/transactions/{id}/status - Update transaction status
GET /admin/transactions/stats - Get transaction statistics
```

### Heatmap Data

```
GET /admin/heatmap-data - Transaction risk heatmap
GET /admin/login-heatmap - Login activity heatmap
GET /admin/user-activity-heatmap - User activity heatmap
```

### System Management

```
GET /admin/system-status - System health and metrics
GET /admin/alerts - System alerts and notifications
PUT /admin/risk-rules - Update risk scoring rules
```

## Security Features

- **Role-Based Access**: Admin-only access with JWT validation
- **Audit Logging**: All admin actions are logged for compliance
- **Session Management**: Secure session handling with timeout
- **CSRF Protection**: All forms protected against CSRF attacks
- **Rate Limiting**: API rate limiting to prevent abuse

## Configuration

### Environment Variables

```bash
# Admin Dashboard
ADMIN_SESSION_TIMEOUT=3600
ADMIN_RATE_LIMIT=100

# Heatmap Settings
HEATMAP_CLUSTER_RADIUS=50
HEATMAP_MAX_ZOOM=18
HEATMAP_TIME_FILTER_DAYS=30

# Risk Rules
DEFAULT_HIGH_THRESHOLD=70
DEFAULT_MEDIUM_THRESHOLD=40
```

### Database Requirements

The admin dashboard requires additional database tables for audit logging and system metrics. Ensure the following tables are created:

- `admin_audit_log`: Logs all admin actions
- `system_metrics`: Stores performance metrics
- `risk_rules`: Stores dynamic risk scoring rules

## Usage Guide

### Accessing the Dashboard

1. Log in with admin credentials
2. Navigate to `/admin` route
3. Dashboard loads with real-time data

### Using Heatmaps

1. Select heatmap type from the dropdown
2. Adjust time filters as needed
3. Zoom and pan to focus on specific areas
4. Click on heatmap points for detailed information
5. Export data for further analysis

### Managing Users

1. Use search bar to find specific users
2. Click on user rows for detailed view
3. Update roles using the role management interface
4. Review user activity and risk history

## Troubleshooting

### Common Issues

- **Heatmap Not Loading**: Check GeoIP database files and Redis connection
- **Slow Performance**: Enable caching and optimize database queries
- **Permission Errors**: Verify admin role assignment and JWT tokens

### Performance Optimization

- Enable Redis caching for heatmap data
- Use database indexes on frequently queried columns
- Implement pagination for large datasets
- Monitor API response times and optimize slow queries
