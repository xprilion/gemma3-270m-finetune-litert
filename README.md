# ⚡ Snippy: Fine-Tuning Gemma 3 270M & Bringing Edge AI to the Browser with LiteRT.js

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/xprilion/gemma3-270m-finetune-litert/blob/main/Colab_Gemma_3_Snippy_LiteRT.ipynb)

An end-to-end tutorial and demo for fine-tuning **Gemma 3 270M** as **Snippy** — an in-browser Code Snippet Generator and UI Tool Calling AI Agent. Snippy runs directly in client web browsers using **Google LiteRT.js** and **WebGPU**, generating executable JavaScript code snippets that manipulate the DOM in real time.

---

## 📑 Table of Contents

1. [Overview & Talk Abstract](#-overview--talk-abstract)
2. [Notebook Options (Colab vs Local)](#-notebook-options-colab-vs-local)
3. [Architecture & Pipeline](#-architecture--pipeline)
4. [Prerequisites](#-prerequisites)
5. [Step-by-Step Tutorial](#-step-by-step-tutorial)
   - [Step 1: Environment Setup](#step-1-environment-setup-google-colab--astral-uv)
   - [Step 2: Fine-Tuning Gemma 3 270M with PEFT / LoRA](#step-2-fine-tuning-gemma-3-270m-with-peft--lora)
   - [Step 3: Merging Adapter Weights](#step-3-merging-adapter-weights)
   - [Step 4: Exporting to LiteRT (`.litertlm`)](#step-4-exporting-to-litert-litertlm)
   - [Step 5: Extracting the WebGPU TFLite FlatBuffer](#step-5-extracting-the-webgpu-tflite-flatbuffer)
   - [Step 6: Setting Up the Web Application](#step-6-setting-up-the-web-application-litertjs--webgpu)
   - [Step 7: Running and Testing Snippy Live](#step-7-running-and-testing-snippy-live)
6. [In-Browser Tool Calling API](#-in-browser-tool-calling-api)
7. [Troubleshooting & Common Pitfalls](#-troubleshooting--common-pitfalls)

---

## 🎯 Overview & Talk Abstract

In this talk, we demonstrate how to fine-tune Gemma models using Google Colab and bring them to the edge with LiteRT.js. We walk through the complete journey from fine-tuning to running a customized Gemma model directly in the browser, enabling fast, private, and practical on-device AI experiences.

**Meet Snippy:** An AI agent that generates JavaScript code snippets to dynamically control the web interface (changing background colors, showing alerts, spawning interactive buttons, and triggering animations like 360° barrel rolls).

---

## 🏗️ Architecture & Pipeline

```
┌─────────────────────────────────────────────────────────┐
│  1. Fine-Tune Gemma 3 270M with LoRA (Colab / PyTorch)  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  2. Merge Adapter Weights (peft.merge_and_unload)       │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  3. Convert Model with LiteRT (litert-torch export_hf)  │
└────────────────────────────┬────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────┐
│  4. Deploy In-Browser Engine (LiteRT.js + WebGPU)      │
└────────────────────────────┴────────────────────────────┘
```

---

## 🛠️ Prerequisites

- **Google Colab** (with T4 GPU) OR a **Local Machine** with Python 3.11+.
- **Astral `uv`** (for fast local environment management).
- **Node.js** (v18+) for running the web application.

---

## 🚀 Step-by-Step Tutorial

### Step 1: Environment Setup (Google Colab / Astral `uv`)

In **Google Colab**:

```bash
# Install ML and LiteRT packages
pip install -q -U torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -q -U transformers peft datasets litert-torch litert-lm
```

For **Local Setup (Astral `uv`)**:

```bash
# Create local virtual environment
uv venv .venv --python 3.11
source .venv/bin/activate

# Install dependencies
uv pip install torch transformers peft trl datasets litert-torch litert-lm jupyter
```

---

### Step 2: Fine-Tuning Gemma 3 270M with PEFT / LoRA

We load `unsloth/gemma-3-270m-it` and fine-tune it on `snippy_dataset.json` using Hugging Face `Trainer`.

```python
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments, DataCollatorForLanguageModeling
from peft import LoraConfig, get_peft_model
from datasets import Dataset

MODEL_ID = "unsloth/gemma-3-270m-it"
OUTPUT_LORA_DIR = "./lora_adapter"
OUTPUT_MERGED_DIR = "./fine_tuned_gemma_merged"

# 1. Load Tokenizer and Base Model
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
    device_map="auto"
)

# 2. Configure LoRA Target Modules
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
peft_model = get_peft_model(model, peft_config)

# 3. Load Training Dataset
with open('snippy_dataset.json', 'r') as f:
    sample_data = json.load(f)

dataset = Dataset.from_list(sample_data)

def tokenize_fn(examples):
    return tokenizer(examples['text'], truncation=True, max_length=256)

tokenized_dataset = dataset.map(tokenize_fn, batched=True, remove_columns=['text'])

# 4. Configure Trainer
training_args = TrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    num_train_epochs=5,
    learning_rate=2e-4,
    logging_steps=1,
    fp16=torch.cuda.is_available(),
    optim="adamw_torch",
    report_to="none"
)

trainer = Trainer(
    model=peft_model,
    train_dataset=tokenized_dataset,
    args=training_args,
    data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)
)
trainer.train()

# 5. Save LoRA Adapter
peft_model.save_pretrained(OUTPUT_LORA_DIR)
tokenizer.save_pretrained(OUTPUT_LORA_DIR)
print("✅ LoRA Adapter Saved!")
```

---

### Step 3: Merging Adapter Weights

> ⚠️ **Critical Requirement:** LiteRT converters cannot process unmerged LoRA adapter folders. You must merge adapter weights back into the base model before converting.

```python
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import torch

base_model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32, device_map="cpu")
peft_model = PeftModel.from_pretrained(base_model, OUTPUT_LORA_DIR)

# Merge weights into base model
merged_model = peft_model.merge_and_unload()

# Save unified safetensors checkpoint
merged_model.save_pretrained(OUTPUT_MERGED_DIR)
tokenizer.save_pretrained(OUTPUT_MERGED_DIR)
print("✅ Merged Checkpoint Saved!")
```

---

### Step 4: Exporting to LiteRT (`.litertlm`)

Use `litert-torch export_hf` to convert the merged PyTorch model to LiteRT FlatBuffer format with dynamic INT8 quantization:

```bash
litert-torch export_hf \
  ./fine_tuned_gemma_merged \
  ./litert_output \
  -b True \
  -q dynamic_int8
```

---

### Step 5: Extracting the WebGPU TFLite FlatBuffer

For in-browser WebGPU execution via `@litertjs/core`, extract the raw TFLite FlatBuffer (starting with `TFL3` magic header) from the bundle container into `./web/public/models/`:

```python
import os
import shutil

SOURCE_MODEL = "./litert_output/model.litertlm"
DEST_DIR = "./web/public/models"

os.makedirs(DEST_DIR, exist_ok=True)
if os.path.exists(SOURCE_MODEL):
    # 1. Copy bundle for Python backend
    shutil.copy(SOURCE_MODEL, os.path.join(DEST_DIR, "model.litertlm"))

    # 2. Extract TFLite FlatBuffer (starts with TFL3 magic) for WebGPU browser runtime
    with open(SOURCE_MODEL, "rb") as f:
        data = f.read()
    pos = data.find(b"TFL3")
    if pos != -1:
        tflite_data = data[pos - 4:]
        with open(os.path.join(DEST_DIR, "model.tflite"), "wb") as f:
            f.write(tflite_data)
        print("✅ Extracted TFLite FlatBuffer to web/public/models/")
```

---

### Step 6: Setting Up the Web Application (LiteRT.js + WebGPU)

#### 1. Security Headers (`web/server.js`)

LiteRT.js requires Cross-Origin Isolation headers (`COOP` and `COEP`) for WebGPU / WASM multithreading:

```javascript
const express = require("express");
const path = require("path");
const app = express();

// Required Headers
app.use((req, res, next) => {
  res.setHeader("Cross-Origin-Opener-Policy", "same-origin");
  res.setHeader("Cross-Origin-Embedder-Policy", "require-corp");
  next();
});

app.use(express.static(path.join(__dirname, "public")));
app.use("/node_modules", express.static(path.join(__dirname, "node_modules")));
app.use(
  "/wasm",
  express.static(path.join(__dirname, "node_modules/@litertjs/core/wasm")),
);

app.listen(8080, "0.0.0.0", () =>
  console.log("🚀 Server running on http://0.0.0.0:8080"),
);
```

#### 2. ES Module Import Map (`web/public/index.html`)

To resolve bare module imports (`@litertjs/core` and `@litertjs/wasm-utils`) natively in browsers without bundlers:

```html
<script type="importmap">
  {
    "imports": {
      "@litertjs/core": "/node_modules/@litertjs/core/dist/index.js",
      "@litertjs/wasm-utils": "/node_modules/@litertjs/wasm-utils/dist/index.js"
    }
  }
</script>
```

#### 3. Client Engine & Action Dispatcher (`web/public/app.js`)

```javascript
import { loadLiteRt } from "@litertjs/core";

// Generic Tool Dispatcher
window.Snippy = {
  executeTool: function (toolName, args = {}) {
    switch (toolName) {
      case "set_background_color":
        document.body.style.backgroundColor = args.color;
        break;
      case "show_notification":
        alert(args.message);
        break;
      case "barrel_roll":
        document.body.style.transition = "transform 1.5s ease";
        document.body.style.transform = "rotate(360deg)";
        break;
    }
  },
};

// Initialize WASM Runtime
await loadLiteRt("/wasm/");
```

---

### Step 7: Running and Testing Snippy Live

```bash
# Navigate to web folder
cd web

# Install node dependencies
npm install

# Start the web server
npm start
```

Open **`http://localhost:8080`** in Chrome/Edge.

#### Try asking Snippy:

- 🌀 _"do a barrel roll"_ -> Rotates the entire webpage 360°!
- 🔴 _"make the background red"_ -> Updates webpage background color!
- 🚀 _"create a button called 'Launch Rocket'"_ -> Spawns an interactive button on the UI!
- 🎉 _"celebrate with confetti!"_ -> Triggers particle confetti animation!

---

## ⚡ In-Browser Tool Calling API

Snippy dispatches all browser actions via `Snippy.executeTool(toolName, args)`:

| Tool Name              | Parameters                                             | Action Executed                    |
| :--------------------- | :----------------------------------------------------- | :--------------------------------- |
| `set_background_color` | `{ color: '#hex' }`                                    | Updates page background color      |
| `show_notification`    | `{ message: 'text', type: 'info\|success' }`           | Displays top banner notification   |
| `create_ui_element`    | `{ tag: 'button\|card', text: 'label', css: 'style' }` | Spawns interactive UI element      |
| `barrel_roll`          | `{}`                                                   | Rotates viewport 360°              |
| `run_javascript`       | `{ code: 'valid JS snippet' }`                         | Evaluates arbitrary DOM JavaScript |

---

## ⚠️ Troubleshooting & Common Pitfalls

1. **Unmerged LoRA Folders:**
   - _Issue:_ `litert-torch` fails on PEFT adapter directories.
   - _Fix:_ Always run `peft_model.merge_and_unload()` first.

2. **Browser Cross-Origin Isolation (`COOP` / `COEP`):**
   - _Issue:_ LiteRT.js WASM multithreading fails to allocate SharedArrayBuffers.
   - _Fix:_ Access the app via `http://localhost:8080` and ensure `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` headers are set in `server.js`.

3. **Bare ES Module Resolution Error:**
   - _Issue:_ `Failed to resolve module specifier "@litertjs/wasm-utils"`.
   - _Fix:_ Include the `<script type="importmap">` block in `index.html`.

4. **V8 ArrayBuffer 2GB Buffer Limit (`source array is too long`):**
   - _Issue:_ Loading unquantized 2B models (> 2 GB) causes V8 TypedArray buffer allocation crashes.
   - _Fix:_ Use **Gemma 3 270M** or INT8 dynamic quantization (`-q dynamic_int8`), keeping model size under ~300 MB.
