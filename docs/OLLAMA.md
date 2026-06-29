# Slate — Ollama Configuration

Slate uses [Ollama](https://ollama.com) for all LLM inference. This document covers model selection, hardware requirements, and tuning.

---

## Model roles

Slate uses three model slots, configured via environment variables:

| Slot | Default | Used for | Config var |
| --- | --- | --- | --- |
| **Fast** | `gemma3:4b` | Capture text parsing, wrap-up extraction | `OLLAMA_FAST_MODEL` |
| **Smart** | `gemma3:12b` | Recaps, Pick reasoning | `OLLAMA_SMART_MODEL` |
| **Vision** | `qwen3-vl:4b` | Photo capture (cover/shelf recognition) | `OLLAMA_VISION_MODEL` |

The fast model handles structured extraction (JSON output) where speed matters more than nuance. The smart model handles free-text generation where quality matters. The vision model handles multimodal image input.

---

## Pulling models

```bash
# Pull the defaults
make ollama-pull

# Or manually
ollama pull gemma3:4b
ollama pull gemma3:12b
ollama pull qwen3-vl:4b
```

---

## Hardware requirements

### CPU-only (no GPU)

| Model | RAM needed | Inference speed (10s audio transcript) |
| --- | --- | --- |
| `gemma3:4b` | ~4 GB | ~3-5s |
| `gemma3:12b` | ~8 GB | ~10-20s |
| `qwen3-vl:4b` | ~4 GB | ~5-10s per image |

A machine with 16 GB RAM can run all three models (Ollama loads/unloads as needed). Recaps and Pick suggestions will be slower but functional.

### GPU (NVIDIA)

| Model | VRAM needed | Inference speed |
| --- | --- | --- |
| `gemma3:4b` | ~3 GB | <1s |
| `gemma3:12b` | ~8 GB | ~2-4s |
| `qwen3-vl:4b` | ~3 GB | ~2-3s per image |

An RTX 3060 (12 GB) or RTX 4060 (8 GB) handles all models comfortably. For cloud GPU instances, an A10G or T4 works well.

### Apple Silicon

Ollama runs natively on Apple Silicon with Metal acceleration. Performance is between CPU and discrete GPU:

| Model | Memory needed | Inference speed |
| --- | --- | --- |
| `gemma3:4b` | ~4 GB unified | ~1-2s |
| `gemma3:12b` | ~8 GB unified | ~3-6s |
| `qwen3-vl:4b` | ~4 GB unified | ~2-4s per image |

M1/M2/M3 with 16 GB unified memory runs the full stack well.

---

## Alternative models

You can swap any model slot. Some tested alternatives:

### Fast model alternatives

| Model | Size | Notes |
| --- | --- | --- |
| `llama3.2:3b` | 3B | Good at JSON extraction, slightly less accurate |
| `phi4-mini` | 3.8B | Strong reasoning for its size |
| `qwen3:4b` | 4B | Good multilingual support |

### Smart model alternatives

| Model | Size | Notes |
| --- | --- | --- |
| `llama3.1:8b` | 8B | Lower VRAM, good recap quality |
| `qwen3:8b` | 8B | Strong reasoning, multilingual |
| `gemma3:27b` | 27B | Best quality, needs ~16 GB VRAM |
| `llama3.3:70b` | 70B | Top quality, needs ~40 GB VRAM |

### Vision model alternatives

| Model | Size | Notes |
| --- | --- | --- |
| `llama3.2-vision:11b` | 11B | More accurate, needs more VRAM |
| `gemma3:12b` | 12B | Gemma 3 has vision capabilities at 12B |

### Downgrade path (minimal hardware)

For machines with only 8 GB RAM and no GPU:

```env
OLLAMA_FAST_MODEL=gemma3:4b
OLLAMA_SMART_MODEL=gemma3:4b     # same model for both
OLLAMA_VISION_MODEL=qwen3-vl:4b
```

Recap quality decreases, but the app remains fully functional. The 4B model produces shorter, less nuanced recaps.

---

## Configuration

### Timeout

```env
LLM_TIMEOUT_SECONDS=60   # default; increase for slow hardware
```

Recaps on CPU with `gemma3:12b` may need 90-120s. Set this higher if you see timeout errors in the logs.

### Ollama base URL

```env
OLLAMA_BASE_URL=http://localhost:11434   # default
```

Change this if Ollama runs on a different machine or port.

### Running Ollama as a service

```bash
# macOS (installed via brew or .app)
ollama serve

# Linux (systemd)
sudo systemctl enable ollama
sudo systemctl start ollama

# Docker
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

### GPU acceleration (Linux)

Install the NVIDIA Container Toolkit, then:

```bash
docker run -d --gpus all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
```

Or if running Ollama directly (not Docker):

```bash
# Ollama auto-detects CUDA GPUs. No extra config needed.
ollama serve
```

---

## Faster-whisper (STT)

Speech-to-text uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper), not Ollama. It runs in-process within the API.

| Config var | Default | Options |
| --- | --- | --- |
| `STT_PROVIDER` | `dummy` | `whisper_local`, `dummy` |
| `WHISPER_MODEL_SIZE` | `base` | `tiny`, `base`, `small`, `medium` |
| `WHISPER_DEVICE` | `cpu` | `cpu`, `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` | `int8`, `float16`, `float32` |

### Model sizes

| Model | Size | Speed (10s audio, CPU) | Accuracy |
| --- | --- | --- | --- |
| `tiny` | 39 MB | ~1s | Low |
| `base` | 74 MB | ~2s | Good |
| `small` | 244 MB | ~5s | Better |
| `medium` | 769 MB | ~15s | Best |

The `base` model is recommended for most setups. Use `small` if transcription accuracy is poor for your language/accent.

---

## LLM provider fallback

Slate supports an alternative LLM provider via `LLM_PROVIDER`:

| Value | Backend | Requires |
| --- | --- | --- |
| `ollama` | Local Ollama instance | Ollama running |
| `dummy` | Deterministic dummy responses | Nothing (used in tests) |

Cloud provider support (e.g., AWS Bedrock) is documented in ARCHITECTURE.md as an optional extension point but not shipped in v1.0.
