const express = require('express');
const path = require('path');
const fs = require('fs');
const { execFile } = require('child_process');

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

// Dynamic Python executable detection (portable across any machine/environment)
const getPythonExecutable = () => {
  if (process.env.PYTHON) return process.env.PYTHON;
  if (process.env.PYTHON_PATH) return process.env.PYTHON_PATH;
  
  // Test local system python paths
  const candidatePaths = [
    '/Users/xprilion/.local/share/uv/tools/jupyterlab/bin/python',
    path.join(__dirname, '..', '.venv', 'bin', 'python'),
    'python3',
    'python'
  ];

  for (const candidate of candidatePaths) {
    if (candidate.startsWith('/') && fs.existsSync(candidate)) {
      return candidate;
    }
  }
  return 'python3';
};

// LiteRT Generation Endpoint
app.post('/api/generate', (req, res) => {
  const prompt = req.body.prompt || '';
  const pythonPath = getPythonExecutable();
  const scriptPath = path.join(__dirname, 'generate.py');
  const modelPath = path.join(__dirname, '..', 'litert_output', 'model.litertlm');

  execFile(pythonPath, [scriptPath, modelPath, prompt], { maxBuffer: 10 * 1024 * 1024 }, (error, stdout, stderr) => {
    if (error) {
      console.error('Generation Error:', error, stderr);
      return res.status(500).json({ success: false, error: error.message });
    }
    try {
      const lines = stdout.trim().split('\n');
      const jsonLine = lines.find(l => l.startsWith('{') && l.endsWith('}'));
      if (jsonLine) {
        const result = JSON.parse(jsonLine);
        return res.json(result);
      }
      return res.json({ success: true, text: stdout });
    } catch (e) {
      return res.json({ success: true, text: stdout });
    }
  });
});

app.listen(PORT, HOST, () => {
  console.log(`🚀 LiteRT.js Snippy Server running at http://${HOST}:${PORT}`);
});
