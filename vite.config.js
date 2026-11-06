import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: 'custom_components/mzkzg_transport/www',
    emptyOutDir: false, // Don't empty the dir so we don't delete mzkzg-transport-card.js (the wrapper)
    lib: {
      entry: 'src/polish-transport-card.js',
      name: 'PolishTransportCard',
      formats: ['es'],
      fileName: () => 'polish-transport-card.js',
    },
    rollupOptions: {
      // Home Assistant handles Lit, but building it locally is safer for standalone cards
      // unless we explicitly want to externalize it. For now we bundle Lit.
    }
  }
});
