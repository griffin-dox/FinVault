# SecureBank - Passwordless Banking MVP

## Overview

SecureBank is a modern, secure banking application that implements passwordless authentication using behavioral profiling and fraud detection. The application features a React-based frontend with a Node.js/Express backend, utilizing PostgreSQL with Drizzle ORM for data persistence. The system captures user behavioral metrics during authentication and transaction processes to provide advanced security through AI-powered risk assessment.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React with TypeScript using Vite as the build tool
- **Routing**: Wouter for client-side routing
- **UI Components**: Radix UI primitives with ShadCN/UI component system
- **Styling**: TailwindCSS with CSS variables for theming
- **State Management**: TanStack Query for server state, React Context for authentication
- **Forms**: React Hook Form with Zod validation
- **Animations**: Framer Motion for enhanced user experience

### Backend Architecture
- **Runtime**: Node.js with Express.js framework (current), Python FastAPI (recommended migration)
- **Language**: TypeScript with ES modules (current), Python 3.11+ (recommended)
- **Database**: PostgreSQL with Drizzle ORM (current), SQLAlchemy with Alembic (recommended)
- **Database Provider**: Neon Database (serverless PostgreSQL)
- **NoSQL Database**: MongoDB for behavioral data and analytics (recommended addition)
- **Caching**: Redis for sessions, rate limiting, and caching (recommended addition)
- **Search**: Elasticsearch for transaction search and fraud detection (recommended addition)
- **Session Management**: In-memory storage with fallback for production PostgreSQL sessions
- **API Design**: RESTful endpoints with JSON communication

### Authentication Strategy
- **Passwordless System**: No traditional passwords required
- **Behavioral Profiling**: Captures typing patterns, mouse movements, and device fingerprints
- **Magic Link**: Email-based verification for initial registration
- **Risk Assessment**: Real-time scoring based on behavioral patterns and device information

## Key Components

### Core Pages
1. **Landing Page** (`/`): Marketing page with registration and login entry points
2. **Registration** (`/register`): User signup with basic information collection
3. **Email Verification** (`/verify-email`): Magic link verification flow
4. **Onboarding** (`/onboarding`): Behavioral data collection and device fingerprinting
5. **Login** (`/login`): Behavioral-based authentication
6. **Dashboard** (`/dashboard`): Main user interface with account overview
7. **Transactions** (`/transactions`): Transaction history and new transfer creation
8. **Admin Panel** (`/admin`): Administrative controls for user and fraud management

### Shared Schema
- **Users Table**: Stores user profiles, verification status, risk levels, and behavioral data
- **Transactions Table**: Records all financial transactions with risk scores
- **Fraud Alerts Table**: Tracks security incidents and suspicious activities

### Behavioral Analysis Features
- **Typing Analysis**: Captures WPM, accuracy, keystroke timing patterns
- **Device Fingerprinting**: Browser, OS, screen resolution, timezone collection
- **Risk Scoring**: Dynamic assessment based on behavioral patterns and transaction context
- **Real-time Monitoring**: Continuous evaluation during user sessions

## Data Flow

### Registration Flow
1. User provides basic information (name, email, phone, country)
2. System generates magic link and sends verification email
3. User clicks verification link to proceed to onboarding
4. Behavioral data collection during onboarding tasks
5. Account activation with behavioral profile creation

### Authentication Flow
1. User enters email on login page
2. System presents behavioral challenges (typing tests, etc.)
3. Real-time behavioral analysis and risk assessment
4. Authentication granted based on behavioral match and risk score
5. Session establishment with continuous monitoring

### Transaction Flow
1. User initiates transfer through dashboard or transactions page
2. System performs real-time risk assessment
3. Behavioral verification may be required for high-risk transactions
4. Transaction processing with fraud monitoring
5. Real-time updates and notifications

## External Dependencies

### Frontend Dependencies
- **UI Framework**: React 18 with TypeScript support
- **Component Library**: Radix UI primitives for accessible components
- **State Management**: TanStack Query for efficient server state management
- **Form Handling**: React Hook Form with Zod schema validation
- **Styling**: TailwindCSS with class-variance-authority for component variants
- **Animation**: Framer Motion for smooth transitions and interactions
- **Date Handling**: date-fns for date manipulation and formatting

### Backend Dependencies
- **Database**: Drizzle ORM with PostgreSQL dialect
- **Session Storage**: connect-pg-simple for PostgreSQL session storage
- **Validation**: Zod for runtime type validation and schema definition
- **Development**: tsx for TypeScript execution in development

### Database Provider
- **Neon Database**: Serverless PostgreSQL with connection pooling
- **Environment**: Database URL configuration through environment variables
- **Migrations**: Drizzle Kit for database schema migrations

## Deployment Strategy

### Development Environment
- **Dev Server**: Vite development server with HMR (Hot Module Replacement)
- **Backend**: tsx for running TypeScript directly in development
- **Database**: Connection to Neon Database development instance
- **Environment**: NODE_ENV=development with development-specific logging

### Production Build Process
1. **Frontend Build**: Vite builds optimized React application to `dist/public`
2. **Backend Build**: esbuild bundles server code with external dependencies
3. **Static Assets**: Frontend served from `dist/public` directory
4. **Server**: Express serves both API routes and static frontend assets

### Production Deployment
- **Runtime**: Node.js production server serving bundled application
- **Database**: PostgreSQL connection with production credentials
- **Session Storage**: PostgreSQL-backed sessions for persistence
- **Security**: Environment-based configuration for sensitive data
- **Performance**: Optimized bundles with code splitting and asset optimization

### Environment Configuration
- **DATABASE_URL**: PostgreSQL connection string for Drizzle ORM
- **NODE_ENV**: Environment flag for development/production behavior
- **Session Configuration**: Secure session management in production environment