import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const rootNodeModules = path.resolve(__dirname, '../../../node_modules');

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
      'react': path.resolve(rootNodeModules, 'react'),
      'react-dom': path.resolve(rootNodeModules, 'react-dom'),
      'react/jsx-runtime': path.resolve(rootNodeModules, 'react/jsx-runtime'),
      '@shared': path.resolve(__dirname, '../../../packages/shared'),
    },
    dedupe: ['react', 'react-dom'],
  },
  server: {
    fs: {
      allow: ['..', '../../../packages'],
    },
    proxy: {
      '/api/auth': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/api/finance': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/finance/, '')
      },
      '/api/ai': {
        target: 'http://localhost:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/ai/, '')
      }
    }
  },
  build: {
    commonjsOptions: {
      include: [/packages\/shared/, /node_modules/],
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime', 'react/jsx-dev-runtime'],
    esbuildOptions: {
      nodePaths: [rootNodeModules],
    },
  },
});
