# VirtualPyTest Frontend

Modern React TypeScript frontend for VirtualPyTest microservices architecture.

## Architecture Overview

This frontend is part of a microservices architecture:
- **`frontend/`** - React TypeScript web interface (this package)
- **`backend_server/`** - Main API server (REST + WebSocket)
- **`backend_host/`** - Host management service
- **`backend_host/`** - Core testing logic
- **`shared/`** - Shared Python utilities (backend only)

The frontend is **completely self-contained** and only communicates with `backend_server` via HTTP/WebSocket APIs.

## Features

- 🎯 **Dashboard**: System overview and quick actions
- 🧪 **Test Management**: Create, edit, and manage test cases
- 📋 **Campaign Management**: Organize test campaigns
- 🌳 **Navigation Editor**: Visual navigation tree management
- 🔧 **Device Control**: Hardware interface management
- 📊 **Monitoring**: Real-time system monitoring

## Technology Stack

- **React 18** with TypeScript
- **Material-UI (MUI)** v5 for components
- **Vite** for build tooling
- **React Router** for navigation
- **React Query** for data fetching
- **Socket.IO** for real-time updates

## Environment Variables

Copy the environment template and fill in your values:

```bash
# Copy template
cp env.example .env

# Edit with your values
nano .env
```

Required environment variables (see `env.example`):

```bash
# Frontend Environment Variables
VITE_CLOUDFLARE_R2_PUBLIC_URL=your_r2_public_url
```

## Development

### Prerequisites

- Node.js 18+ and npm
- backend_server running on port 5109 (default)

### Quick Start

```bash
# Install dependencies
npm install

# Copy environment config
cp .env.example .env

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

### Environment Configuration

Create a `.env` file with:

```bash
VITE_SERVER_URL=http://localhost:5109  # backend_server URL
VITE_DEV_MODE=true                  # Development mode
```

### Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## Deployment

### Vercel (Recommended)

#### Prerequisites
- GitHub repository with your code
- Vercel account (free tier available)
- Backend server deployed and accessible

#### Step-by-Step Vercel Deployment

1. **Import Project to Vercel**
   - Go to [vercel.com](https://vercel.com) and sign in
   - Click "New Project" → "Import Git Repository"
   - Select your repository (e.g., `virtualpytest`)

2. **Configure Build Settings**
   ```
   Framework Preset: Vite
   Root Directory: frontend
   Build Command: npm run build (auto-detected)
   Output Directory: dist (auto-detected)
   Install Command: npm install (auto-detected)
   ```

3. **Set Environment Variables**
   In Vercel dashboard → Project Settings → Environment Variables:
   ```bash
   VITE_SERVER_URL=https://your-backend-server-url.com
   VITE_CLOUDFLARE_R2_PUBLIC_URL=your_r2_public_url
   ```

4. **Deploy**
   - Click "Deploy" - Vercel will build and deploy automatically
   - Future git pushes to your main branch will auto-deploy

#### Important Vercel Configuration Notes

- ✅ **Root Directory**: Must be set to `frontend` (not project root)
- ✅ **Framework**: Vite (auto-detected)
- ✅ **Node.js Version**: 18.x or higher
- ✅ **Build Output**: `dist/` folder contains all static files
- ✅ **Environment Variables**: All `VITE_*` variables are build-time only

#### Troubleshooting Vercel Deployment

**Error: "Could not read package.json"**
- Solution: Set Root Directory to `frontend` in project settings

**Build Fails with TypeScript Errors**
- Solution: Run `npm run build` locally first to fix TS errors
- Check our build passes: `npx tsc --noEmit`

**Error: "Cannot find namespace 'NodeJS'"**
- Solution: Ensure `@types/node` is in devDependencies
- This is required for timer types (`NodeJS.Timeout`)

**Environment Variables Not Working**
- Ensure variables start with `VITE_` prefix
- Set in Vercel dashboard, not in code
- Redeploy after adding new variables

### Manual Build

```bash
# Build static files
npm run build

# Serve static files
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── components/     # React components
│   ├── pages/         # Page components
│   ├── hooks/         # Custom hooks
│   ├── contexts/      # React contexts
│   ├── services/      # API services
│   ├── types/         # TypeScript types
│   ├── utils/         # Utility functions
│   └── styles/        # CSS styles
├── public/            # Static assets
├── dist/             # Built output (gitignored)
├── package.json      # Dependencies and scripts
├── vite.config.ts    # Vite configuration
├── tsconfig.json     # TypeScript configuration
└── .env              # Environment variables (create from .env.example)
```

**Note**: The `dist/` folder is automatically generated during build and should not be committed to git (already in `.gitignore`).

## API Integration

The frontend communicates with backend_server via:

- **REST API**: `/api/*` endpoints
- **WebSocket**: Real-time updates via Socket.IO
- **File Upload**: Direct file operations

See `src/services/apiClient.ts` for API implementation.

## Development Tips

1. **Hot Reload**: Changes auto-reload in development
2. **API Proxy**: Vite proxies `/api` to backend_server
3. **Type Safety**: Full TypeScript support
4. **Error Handling**: Centralized error management
5. **State Management**: React Query for server state

## Production Considerations

- Built files are optimized and minified
- Source maps included for debugging
- Chunked bundles for faster loading
- Environment variables baked into build
- CORS properly configured for API calls 