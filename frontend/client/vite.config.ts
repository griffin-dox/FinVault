import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { copyFileSync } from "fs";

export default defineConfig({
  base: '/',
  plugins: [
    react(),
    {
      name: 'copy-static-json',
      writeBundle() {
        copyFileSync('static.json', 'dist/static.json');
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
    outDir: "dist", // Output to frontend/client/dist
    emptyOutDir: true,
    chunkSizeWarningLimit: 1000, // Increase warning limit to 1MB
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
});