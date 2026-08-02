import { defineConfig } from 'vite';
import dts from 'vite-plugin-dts';

export default defineConfig({
  build: {
    lib: {
      entry: 'src/index.ts',
      name: 'WidgetClient',
      formats: ['iife', 'es'],
      fileName: (format) => format === 'iife' ? 'widget.iife.js' : 'widget.esm.js',
    },
    sourcemap: true,
    minify: 'esbuild',
    target: ['chrome90', 'firefox88', 'safari14', 'edge90'],
    rollupOptions: {
      output: {
        // Ensure IIFE does not include module-specific output settings
      },
    },
  },
  plugins: [
    dts({
      include: ['src'],
      outDir: 'dist',
      insertTypesEntry: true,
    }),
  ],
});
