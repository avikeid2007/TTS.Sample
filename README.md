# 🎙️ IndicF5 TTS — Web App

A local web application for **high-quality, near-human Text-to-Speech** synthesis across 11 Indian languages, powered by [ai4bharat/IndicF5](https://huggingface.co/ai4bharat/IndicF5) and served via a FastAPI backend.

---

## ✨ Features

- 🌐 **11 Indian languages** — Assamese, Bengali, Gujarati, Hindi, Kannada, Malayalam, Marathi, Odia, Punjabi, Tamil, Telugu
- 🧬 **Zero-shot voice cloning** — clone any voice from a short reference audio clip
- ⚡ **CUDA-accelerated** — automatically uses GPU if available, falls back to CPU
- 🎧 **In-browser playback** — listen to output directly without downloading
- ⬇️ **WAV download** — save the generated audio to disk
- 🖱️ **Drag-and-drop audio upload** — supports WAV and MP3 reference clips
- 📝 **Sample sentences** — one-click language pills pre-fill example text

---

## 🖥️ Demo UI

```
┌─────────────────────────────────────────────────┐
│         IndicF5 TTS  ·  11 languages             │
├─────────────────────────────────────────────────┤
│  Language  [ Hindi ] [ Tamil ] [ Telugu ] ...    │
│                                                  │
│  Text to synthesize                              │
│  ┌─────────────────────────────────────────┐    │
│  │ नमस्ते! संगीत की तरह जीवन भी ...      │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  Reference audio  (drop WAV / MP3 here)          │
│  ┌─────────────────────────────────────────┐    │
│  │  🎙️  Drop file or click to browse      │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  Transcript of reference audio                   │
│  ┌─────────────────────────────────────────┐    │
│  │ ...                                     │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│            ⚡  Generate Speech                   │
│                                                  │
│  Output Audio  ────────────────────────────────  │
│  [▶ ──────────────────────────────── 0:04]       │
│                    ⬇️  Download WAV              │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone / open the project

```powershell
cd D:\TTS.Sample
```

### 2. Create and activate a virtual environment *(recommended)*

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

> **Note:** The `f5_tts` package is installed directly from GitHub and the
> `numpy<=1.26.4` constraint is skipped because numpy 2.x works fine at runtime.

### 4. Start the server

```powershell
.\run.ps1
```

Or manually:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

With hot-reload during development:

```powershell
.\run.ps1 -Reload
```

### 5. Open the app

Navigate to **[http://localhost:8000](http://localhost:8000)** in your browser.

---

## 📡 API Reference

### `GET /health`

Returns model status and active compute device.

**Response:**
```json
{
  "status": "ok",
  "model_loaded": true,
  "device": "cuda:0"
}
```

---

### `POST /synthesize`

Synthesizes speech from text using a reference audio clip.

| Field | Type | Description |
|-------|------|-------------|
| `text` | `string` (form) | Text to synthesize |
| `ref_text` | `string` (form) | Transcript of the reference audio |
| `ref_audio` | `file` (multipart) | Reference WAV or MP3 clip |

**Response:** `audio/wav` binary stream (24 kHz, float32)

**Example with `curl`:**
```bash
curl -X POST http://localhost:8000/synthesize \
  -F "text=नमस्ते! संगीत की तरह जीवन भी खूबसूरत होता है।" \
  -F "ref_text=Your reference transcript here" \
  -F "ref_audio=@path/to/reference.wav" \
  --output output.wav
```

---

## 🗂️ Project Structure

```
TTS.Sample/
├── main.py             # FastAPI app — model loading, API routes, torchaudio patch
├── requirements.txt    # All Python dependencies
├── run.ps1             # PowerShell start script
├── .gitignore
└── static/
    └── index.html      # Single-page browser UI (vanilla HTML/CSS/JS)
```

Directories created at runtime (auto-cleaned on shutdown):

```
uploads/    # Temporary reference audio files (per-request)
outputs/    # Temporary generated WAV files (per-request)
```

---

## ⚙️ How It Works

```
Browser  ──POST /synthesize──►  FastAPI (main.py)
                                    │
                          save ref audio to uploads/
                                    │
                          tts_model(text, ref_audio, ref_text)
                                    │
                          IndicF5 (DiT + Vocos vocoder)
                          runs on CUDA if available
                                    │
                          write 24kHz WAV to outputs/
                                    │
Browser  ◄── stream audio/wav ──────┘
```

The model performs **zero-shot voice cloning**: it uses the prosody, timbre, and speaking style of the reference clip to synthesize the target text in the same voice — no fine-tuning required.

---

## 🛠️ Known Patches

### torchaudio ≥ 2.9 — torchcodec removed

torchaudio 2.9+ hard-wires `torchcodec` as the only audio backend and ignores the `backend` parameter. Since `torchcodec` is not available on all platforms, `main.py` monkey-patches `torchaudio.load` at import time with a pure-`soundfile` implementation:

```python
# main.py — applied before any f5_tts import
import torchaudio as _ta
_ta.load = _soundfile_load   # soundfile-based replacement
```

### CUDA device placement

`AutoModel.from_pretrained` loads safetensors weights onto CPU by default, overwriting CUDA tensors set in `__init__`. The fix is an explicit `.to("cuda")` call after loading:

```python
tts_model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
if device == "cuda":
    tts_model = tts_model.to(device)
```

---

## 📋 Requirements

| Requirement | Minimum |
|-------------|---------|
| Python | 3.10 |
| PyTorch | 2.0 |
| VRAM (GPU) | ~4 GB |
| RAM (CPU) | ~8 GB |
| CUDA *(optional)* | 11.8+ |

---

## 📜 License

This project is released under the **MIT License**.

The underlying model weights — [ai4bharat/IndicF5](https://huggingface.co/ai4bharat/IndicF5) — are also MIT-licensed.

> **Terms of Use:** By using this application you agree to only clone voices for which you have explicit permission. Unauthorized voice cloning is strictly prohibited.

---

## 🙏 Credits

- **IndicF5 model** — [AI4Bharat](https://github.com/AI4Bharat/IndicF5) (Praveen S V, Srija Anand, Soma Siddhartha, Mitesh M. Khapra)
- **F5-TTS architecture** — [SWivid/F5-TTS](https://github.com/SWivid/F5-TTS)
- **Training data** — [Rasa](https://huggingface.co/datasets/ai4bharat/Rasa), [IndicTTS](https://www.iitm.ac.in/donlab/indictts/database), [LIMMITS](https://sites.google.com/view/limmits24/), [IndicVoices-R](https://huggingface.co/datasets/ai4bharat/indicvoices_r)
