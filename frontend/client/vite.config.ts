import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { copyFileSync, existsSync } from "fs";

export default defineConfig({
  base: '/',
  plugins: [
    react(),
    {
      name: 'copy-static-files',
      writeBundle() {
        // Copy static.json for Render
        if (existsSync('static.json')) {
          copyFileSync('static.json', 'dist/static.json');
        }
        // Copy _redirects for alternative hosting platforms
        if (existsSync('public/_redirects')) {
          copyFileSync('public/_redirects', 'dist/_redirects');
        }
        // Copy vercel.json for Vercel and other platforms
        if (existsSync('vercel.json')) {
          copyFileSync('vercel.json', 'dist/vercel.json');
        }
        // Copy test.html for debugging
        if (existsSync('public/test.html')) {
          copyFileSync('public/test.html', 'dist/test.html');
        }
      }
    }
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@shared": path.resolve(__dirname, "shared"),
      "@assets": path.resolve(__dirname, "../../attached_assets"),
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1000,
    sourcemap: false, // Disable source maps in production for security
    minify: 'terser', // Use terser for better minification
    terserOptions: {
      compress: {
        drop_console: true, // Remove console.log in production
        drop_debugger: true,
      },
    },
    rollupOptions: {
      output: {
        entryFileNames: `assets/[name]-[hash].js`,
        chunkFileNames: `assets/[name]-[hash].js`,
        assetFileNames: `assets/[name]-[hash].[ext]`,
        manualChunks: {
          // Split vendor libraries into separate chunks
          'react-vendor': ['react', 'react-dom'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-select', '@radix-ui/react-toast'],
          'query-vendor': ['@tanstack/react-query'],
          'utils-vendor': ['date-fns', 'lucide-react', 'clsx', 'tailwind-merge']
        }
      }
    }
  },
  // Production optimizations
  define: {
    __DEV__: false,
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ['react', 'react-dom', '@tanstack/react-query'],
  },
});