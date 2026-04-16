import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { promisify } from "node:util";
import { brotliCompress } from "node:zlib";
import gzipPlugin from "rollup-plugin-gzip";

const brotliPromise = promisify(brotliCompress);

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    outDir: '../static',
    emptyOutDir: true,
  },
  plugins: [
    // https://github.com/kryops/rollup-plugin-gzip?tab=readme-ov-file#brotli-compression
    gzipPlugin({
        customCompression: (content) => brotliPromise(Buffer.from(content)),
        fileName: ".br",
    }),
    vue()
  ],
  server: {
    open: '/',
    proxy: {
      '/api': {
        target: 'http://localhost:4000',
        changeOrigin: true
      }
    }
  },
})
