import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    // `environmentMatchGlobs` was removed in vitest 4 (deprecated since v3) and is
    // silently ignored, so per-directory environment selection is done via the
    // `// @vitest-environment jsdom` docblock pragma in each file under
    // __tests__/components/ instead. Default stays "node" for everything else.
    environment: "node",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
