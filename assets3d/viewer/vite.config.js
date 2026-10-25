import { defineConfig } from 'vite';
import path from 'path';
const here = import.meta.dirname || path.dirname(new URL(import.meta.url).pathname.slice(1));
// root = viewer/, GLBs of the pack are served at /<name>.glb; any agent GLB via /@fs/<absolute path>
export default defineConfig({
  root: here,
  publicDir: path.resolve(here, '../export'),
  server: { port: 5199, strictPort: true, fs: { strict: false, allow: [path.resolve(here, '..'), path.resolve(here, '../..')] } },
});
