import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

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
      'react': path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
      'react/jsx-runtime': path.resolve(__dirname, 'node_modules/react/jsx-runtime'),
      '@shared': path.resolve(__dirname, '../../packages/shared'),
    },
  },
  server: {
    fs: {
      allow: ['..', '../../packages'],
    },
  },
  build: {
    commonjsOptions: {
      include: [/packages\/shared/, /node_modules/],
    },
  },
});