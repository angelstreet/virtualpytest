import fs from 'fs';
import { execSync } from 'child_process';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Auto-detect HTTPS based on server URL environment variable
const serverUrl = process.env.VITE_SERVER_URL || 'http://localhost:5109';
const shouldUseHttps = serverUrl.startsWith('https://');

// Get user home directory dynamically
const userHome = process.env.HOME || process.env.USERPROFILE || process.cwd();

// Certificate paths - check multiple locations
const certificatePaths = [
  // User-specific certificate paths (dynamic)
  {
    cert: `${userHome}/vite-certs/fullchain.pem`,
    key: `${userHome}/vite-certs/privkey.pem`
  },
  {
    cert: `${userHome}/.ssl/cert.pem`,
    key: `${userHome}/.ssl/key.pem`
  },
  // Project-relative certificate paths
  {
    cert: 'cert.pem',
    key: 'key.pem'
  },
  {
    cert: 'ssl/cert.pem',
    key: 'ssl/key.pem'
  },
  {
    cert: 'certs/cert.pem',
    key: 'certs/key.pem'
  },
  // Environment-specific paths
  {
    cert: process.env.SSL_CERT_PATH || '',
    key: process.env.SSL_KEY_PATH || ''
  },
  // System certificate paths
  {
    cert: '/etc/ssl/certs/server.crt',
    key: '/etc/ssl/private/server.key'
  }
];

// Find available certificates
let certPath = '';
let keyPath = '';
let hasCertificates = false;

for (const paths of certificatePaths) {
  // Skip empty paths from environment variables
  if (!paths.cert || !paths.key) {
    continue;
  }
  if (fs.existsSync(paths.cert) && fs.existsSync(paths.key)) {
    certPath = paths.cert;
    keyPath = paths.key;
    hasCertificates = true;
    console.log(`✅ SSL certificates found: ${certPath}`);
    break;
  }
}

if (shouldUseHttps && !hasCertificates) {
  console.log('⚠️ HTTPS requested but no certificates found - Vite will generate self-signed certificates');
}

// Kill any process using port 5073 synchronously
const killPort5073 = () => {
  try {
    const pids = execSync('lsof -ti:5073', { encoding: 'utf8' }).trim();
    if (pids) {
      console.log('🛑 Killing processes on port 5073...');
      execSync(`kill -9 ${pids}`, { encoding: 'utf8' });
      console.log('✅ Port 5073 is now available');
      // Wait a moment for the port to be fully released
      execSync('sleep 1');
    } else {
      console.log('✅ Port 5073 is already available');
    }
  } catch (error) {
    // No processes found on port 5073, which is what we want
    console.log('✅ Port 5073 is already available');
  }
};

// Kill port before starting - this will block until complete
killPort5073();

// Define registered frontend routes (must match your React Router routes)
const registeredRoutes = [
  '/',
  '/rec',
  '/test-plan/test-cases',
  '/test-plan/campaigns',
  '/test-plan/collections',
  '/test-execution/run-tests',
  '/test-execution/monitoring',
  '/test-results/reports',
  '/test-results/model-reports',
  '/test-results/dependency-report',
  '/configuration',
  '/configuration/',
  '/configuration/devices',
  '/configuration/models',
  '/configuration/interface',
  '/configuration/controller',
  '/configuration/library',
  '/configuration/environment',
  // Dynamic routes patterns
  '/navigation-editor', // Will match /navigation-editor/* paths
  '/docs', // Will match /docs/* paths for documentation including security reports
];

export default defineConfig({
  plugins: [
    react(),
    // Custom plugin for route validation
    {
      name: 'route-validator',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          const url = req.url || '';

          // Skip static assets, API routes, and other proxied paths
          if (
            url.startsWith('/assets/') ||
            url.startsWith('/server/') ||
            url.startsWith('/host/') ||
            url.startsWith('/websockify') ||
            url.includes('.') // Static files (js, css, images, etc.)
          ) {
            return next();
          }

          // Check if the route is registered
          const isRegisteredRoute = registeredRoutes.some((route) => {
            if (route === url) return true;
            if (route.endsWith('/') && url.startsWith(route)) return true;
            if (route === '/navigation-editor' && url.startsWith('/navigation-editor/'))
              return true;
            if (route === '/docs' && url.startsWith('/docs/'))
              return true;
            return false;
          });

          if (!isRegisteredRoute) {
            // Return 404 for unregistered routes
            res.statusCode = 404;
            res.setHeader('Content-Type', 'text/html');
            res.end(`
              <!DOCTYPE html>
              <html>
                <head>
                  <title>404 - Page Not Found</title>
                  <meta name="robots" content="noindex">
                </head>
                <body>
                  <h1>404 - Page Not Found</h1>
                  <p>The requested page does not exist.</p>
                  <a href="/">Return to Dashboard</a>
                </body>
              </html>
            `);
            return;
          }

          next();
        });
      },
    },
  ],
  server: {
    host: '0.0.0.0',
    port: 5073,
    strictPort: true, // Don't try other ports if 5073 is unavailable
    allowedHosts: ['virtualpytest.com', 'www.virtualpytest.com', 'dev.virtualpytest.com', 'virtualpytest-server.onrender.com', 'virtualpytest.vercel.app', '*.vercel.app', 'localhost', '127.0.0.1', '192.168.1.103', '192.168.1.34'],
    https: shouldUseHttps
      ? hasCertificates
        ? {
            key: fs.readFileSync(keyPath),
            cert: fs.readFileSync(certPath),
          }
        : undefined // Let Vite generate self-signed certificates
      : undefined, // No HTTPS
    // Configure how the dev server handles routing
    fs: {
      strict: false,
    },
    // Configure CORS headers for cross-origin requests (including Grafana embedding)
    cors: {
      origin: true, // Allow all origins in development
      credentials: true, // Allow cookies to be sent with requests
    },
    // Add headers to support embedding in iframes and mixed content
    headers: {
      'X-Frame-Options': 'SAMEORIGIN',
      // Local dev: Remove upgrade-insecure-requests to allow HTTP
      'Content-Security-Policy': shouldUseHttps 
        ? "frame-ancestors 'self' http://localhost:3000 https://localhost:3000 https://dev.virtualpytest.com https://virtualpytest.com; upgrade-insecure-requests"
        : "frame-ancestors 'self' http://localhost:3000 http://localhost:6109",
    },
  },
  // Configure build for proper SPA handling
  build: {
    rollupOptions: {
      input: {
        main: './index.html',
      },
    },
  },
});
