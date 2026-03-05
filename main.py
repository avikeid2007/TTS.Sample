import os
import uuid
import shutil
import logging
import numpy as np
import soundfile as sf

# ── Patch torchaudio.load to avoid torchcodec dependency ─────────────────────
# torchaudio 2.9+ hardwires torchcodec and ignores the `backend` parameter.
# Replace torchaudio.load entirely with a soundfile-based implementation.
import torch as _torch
import torchaudio as _ta
import soundfile as _sf_ta
import numpy as _np_ta

def _soundfile_load(uri, frame_offset=0, num_frames=-1, normalize=True,
                    channels_first=True, format=None, buffer_size=4096,
                    backend=None):
    src = str(uri) if not hasattr(uri, "read") else uri
    data, sr = _sf_ta.read(src, dtype="float32", always_2d=True)
    # data: [time, channels]
    if frame_offset > 0:
        data = data[frame_offset:]
    if num_frames > 0:
        data = data[:num_frames]
    tensor = _torch.from_numpy(_np_ta.ascontiguousarray(data))
    if channels_first:
        tensor = tensor.T   # → [channels, time]
    return tensor, sr

_ta.load = _soundfile_load

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── Directories ──────────────────────────────────────────────────────────────
UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Model (loaded once at startup) ───────────────────────────────────────────
tts_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global tts_model
    log.info("Loading IndicF5 model …")
    try:
        from transformers import AutoModel
        tts_model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True)
        log.info("IndicF5 model loaded successfully.")
    except Exception as exc:
        log.error("Failed to load IndicF5 model: %s", exc)
        log.warning("The /synthesize endpoint will return 503 until the model is available.")
    yield
    # cleanup
    shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="IndicF5 TTS", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "model_loaded": tts_model is not None}


@app.post("/synthesize")
async def synthesize(
    text: str = Form(..., description="Text to synthesize"),
    ref_text: str = Form(..., description="Transcript of the reference audio"),
    ref_audio: UploadFile = File(..., description="Reference audio file (WAV/MP3)"),
):
    if tts_model is None:
        raise HTTPException(status_code=503, detail="Model is not loaded yet. Please try again shortly.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="'text' must not be empty.")
    if not ref_text.strip():
        raise HTTPException(status_code=400, detail="'ref_text' must not be empty.")

    # ── Save uploaded reference audio ────────────────────────────────────────
    req_id = uuid.uuid4().hex
    suffix = Path(ref_audio.filename).suffix or ".wav"
    ref_path = UPLOAD_DIR / f"{req_id}_ref{suffix}"
    out_path = OUTPUT_DIR / f"{req_id}_out.wav"

    try:
        with ref_path.open("wb") as f:
            shutil.copyfileobj(ref_audio.file, f)

        log.info("[%s] Synthesizing: %r", req_id, text[:80])

        # ── Run inference ────────────────────────────────────────────────────
        audio = tts_model(
            text,
            ref_audio_path=str(ref_path),
            ref_text=ref_text,
        )

        # ── Normalise & write output WAV ─────────────────────────────────────
        if isinstance(audio, (list, tuple)):
            audio = audio[0]
        audio = np.array(audio, dtype=np.float32)
        if audio.dtype == np.int16 or audio.max() > 1.0:
            audio = audio.astype(np.float32) / 32768.0

        sf.write(str(out_path), audio, samplerate=24000)
        log.info("[%s] Audio saved to %s", req_id, out_path)

    except HTTPException:
        raise
    except Exception as exc:
        log.exception("[%s] Synthesis error", req_id)
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {exc}") from exc
    finally:
        if ref_path.exists():
            ref_path.unlink(missing_ok=True)

    return FileResponse(
        path=str(out_path),
        media_type="audio/wav",
        filename="output.wav",
        headers={"X-Request-Id": req_id},
    )
