import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
import { tanstackStart } from '@tanstack/react-start/plugin/vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import tsconfigPaths from 'vite-tsconfig-paths';
import { nitro } from 'nitro/vite';

// This file lives in config/; the project root is one level up.
const root = fileURLToPath(new URL('..', import.meta.url));

export default defineConfig({
  root,
  plugins: [
    tsconfigPaths({ root }),
    tanstackStart({ srcDirectory: 'src/web', server: { entry: 'server' } }),
    react(),
    tailwindcss(),
    nitro({ preset: 'node-server' }),
  ],
  resolve: { dedupe: ['react', 'react-dom', '@tanstack/react-router'] },
  server: { port: 3000 },
});
