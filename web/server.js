const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const HOST = process.env.HOST || '0.0.0.0';
const PORT = process.env.PORT || 8080;

app.use(express.json());

// REQUIRED HEADERS for WebGPU and WebAssembly multithreading
app.use((req, res, next) => {
  res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
  res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
  next();
});

// Silence favicon 404 warnings
app.get('/favicon.ico', (req, res) => res.status(204).end());

// Smart fallback for @litertjs/wasm-utils across hoisted & non-hoisted npm tree structures
app.use('/node_modules/@litertjs/wasm-utils', (req, res, next) => {
  const topPath = path.join(__dirname, 'node_modules/@litertjs/wasm-utils', req.path);
  const nestedPath = path.join(__dirname, 'node_modules/@litertjs/core/node_modules/@litertjs/wasm-utils', req.path);
  if (fs.existsSync(topPath) && fs.statSync(topPath).isFile()) {
    return res.sendFile(topPath);
  } else if (fs.existsSync(nestedPath) && fs.statSync(nestedPath).isFile()) {
    return res.sendFile(nestedPath);
  }
  next();
});

// Serve static assets and node_modules
app.use(express.static(path.join(__dirname, 'public')));
app.use('/node_modules', express.static(path.join(__dirname, 'node_modules')));
app.use('/wasm', express.static(path.join(__dirname, 'node_modules/@litertjs/core/wasm')));

app.listen(PORT, HOST, () => {
  console.log(`🚀 LiteRT.js Pure WebAssembly Snippy Server running at http://${HOST}:${PORT}`);
});
