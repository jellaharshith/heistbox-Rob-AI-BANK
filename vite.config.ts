import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], optimizeDeps: { entries:['index.html'] }, server: { port: 5173, watch:{ ignored:['**/assets3d/**','**/web/**','**/baseline_frontend/**','**/_trash/**','**/training/**','**/.git/**','**/.venv/**','**/db/**'] }, proxy: { '/api': 'http://localhost:8000', '/ws': { target: 'ws://localhost:8000', ws: true } } } });

