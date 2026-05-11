import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';
const localNodeModules = path.resolve(__dirname, 'node_modules');

export default defineConfig({
  plugins: [
    react({
      // This is the magic line for monorepos!
      // It ensures shared packages use the same React version as the frontend.
      jsxRuntime: 'automatic', 
    })
  ],
  resolve: {
    alias: {
      'lucide-react': path.resolve(localNodeModules, 'lucide-react'),
      'clsx': path.resolve(localNodeModules, 'clsx'),
      'tailwind-merge': path.resolve(localNodeModules, 'tailwind-merge'),
      '@shared': path.resolve(__dirname, '../shared'),
    },
    dedupe: ['react', 'react-dom'],
  },
  server: {
    host: '0.0.0.0',
    watch: process.platform === 'win32'
      ? {
          usePolling: true,
          interval: 200,
        }
      : undefined,
    fs: {
      allow: ['..', '../shared'],
    },
    proxy: {
      '/auth': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/finance': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/ai': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/tora': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/mcp': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
      '/api/auth': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/auth/, '/auth')
      },
      '/api/finance': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/finance/, '/finance')
      },
      '/api/ai': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/ai/, '/ai')
      }
    }
  },
  build: {
    commonjsOptions: {
      include: [/shared\//, /node_modules/],
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime'],
    esbuildOptions: {
      nodePaths: [localNodeModules],
    },
  },
});
