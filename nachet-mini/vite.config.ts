import path from "path";
import fs from 'fs';
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  base: process.env.VITE_BASE_URL || "/",
  plugins: [react(),
    {
      name: 'models-404',
      configureServer(server) {
        server.middlewares.use('/models', (req, res, next) => {
          const urlPath = req.url ? decodeURIComponent(req.url.split('?')[0]) : '/';
          const filePath = path.join(process.cwd(), 'public', 'models', urlPath);

          if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
            return next();
          }

          res.statusCode = 404;
          res.setHeader('Content-Type', 'text/plain');
          res.end('Not found');
        });
      },
    },],
  optimizeDeps: {
    include: [
      "@mui/icons-material/GitHub",
      "@mui/icons-material/Close",
      "react-webcam",
    ],
  },
  resolve: {
    alias: {
      "@common": path.resolve(__dirname, "src/common"),
      "@components": path.resolve(__dirname, "src/components"),
      "@hooks": path.resolve(__dirname, "src/hooks"),
      "@stores": path.resolve(__dirname, "src/stores"),
      "@inference": path.resolve(__dirname, "src/inference"),
    },
  },
});
