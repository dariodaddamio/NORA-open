# Stack and costs

Back to main [README](../README.md) · [All docs](README.md)

NORA keeps heavy lifting local where possible (download, ffmpeg, Whisper, optional Tesseract) and uses an LLM via **OpenRouter** or **Ollama**. Env knobs are documented in [configuration.md](configuration.md) and [`.env.example`](../.env.example).

| Tier | What runs where | When to use |
|------|-----------------|-------------|
| **Default (low recurring cost)** | Local: `ffmpeg`, `faster-whisper`, optional `tesseract`. LLM: **OpenRouter** (pick a model — free tiers vary by provider). | Day-to-day; good balance of quality and cost. |
| **Stronger summaries** | Same local stack; set `OPENROUTER_MODEL` to a **paid / stronger** model on OpenRouter. | When free models are too vague or inconsistent. |
| **Local / privacy LLM** | Omit `OPENROUTER_API_KEY`; use **Ollama** (`OLLAMA_MODEL`). | Keep prompts and completions on your machine. |
| **More cloud (extension point)** | Today, speech-to-text is **local Whisper**. A fully hosted pipeline would swap `transcribe_audio` in `process_link.py` for a cloud STT API — not shipped as a preset, but that is the natural seam if you want zero local ML. | Advanced self-hosting or fork. |

OpenRouter billing and model availability are defined by their service. Local tools need Python, ffmpeg, and (for OCR) Tesseract on your PATH or via `OCR_TESSERACT_CMD`.

## Keyframes and OCR (limits and improvements)

**What NORA does today:** `ffmpeg` grabs still frames; **[Tesseract](https://github.com/tesseract-ocr/tesseract)** runs **classic OCR** on each JPEG. Only the **extracted text** (plus timestamps) is pasted into the LLM prompts for classify / entities / summary. The model does **not** see the raw images as a vision model would. Frames you keep are still saved under `Assets/Instagram/...` for **## Visual Highlights** in the note, but that is for *you* in Obsidian—not pixel-level understanding inside the pipeline.

**Why it often looks weak:** stylized fonts, tiny UI text, motion blur, busy layouts, memes, and non-English (without extra Tesseract language packs) produce empty or garbage OCR—so “visual context” in prompts is thin even when the reel is very visual.

**Improve without changing code**

- Tune sampling: `FRAME_SAMPLING_MODE=scene`, more `MAX_KEYFRAMES_ANALYZED`, tighter or looser `FRAME_INTERVAL_SECONDS` (interval mode)—see [configuration.md](configuration.md).
- Install a solid Tesseract build and add languages if you need them; set `OCR_TESSERACT_CMD` if it is not on PATH.
- Use a **stronger text LLM** (`OPENROUTER_MODEL` on a paid or larger model, or a capable local Ollama model): it cannot fix OCR errors, but it can sometimes reason better from sparse on-screen hints.
- Turn on **`CONSISTENCY_CHECK_ENABLED`** (and related knobs) so weak OCR + transcript mismatches are flagged rather than silently invented.

**Improve with money or GPU (needs more than env vars)**

- **True video understanding** (model looks at pixels) would require extending the pipeline—for example sending frame images to a **vision-capable** chat API in `process_link.py` (OpenRouter and others support image+text for some models). That is **not** wired up today; it is a deliberate fork/extension point—see [extending.md](extending.md).
- **Better OCR** (cloud OCR, custom layout models, etc.) would also be a **code change**: replace or augment `_ocr_image_text` / `analyze_frames_with_ocr` rather than only tuning Tesseract.

If on-screen content is critical for your vault, treat transcript + caption as primary and use OCR-backed notes as a **bonus** until you invest in a vision-capable path.
