# How it works

Back to main [README](../README.md) · [All docs](README.md)

NORA is a local pipeline: Discord triggers a download of the reel, optional **keyframes + Tesseract OCR** (text snippets into prompts, not a vision model), local transcription, quality gates, then text LLM steps that classify and summarize into markdown your Obsidian vault can link together.

## System context

```mermaid
flowchart LR
  discord[Discord_slash_commands] --> bot[bot_py]
  bot --> ytdlp[yt_dlp_download]
  bot --> ffmpeg[ffmpeg_audio_frames]
  bot --> whisper[faster_whisper]
  bot --> ocr[tesseract_OCR_optional]
  bot --> llm[OpenRouter_or_Ollama]
  bot --> vault[Obsidian_vault_markdown]
```

## Pipeline and gates

```mermaid
flowchart TD
  A[Download_video] --> B[Keyframes_OCR_optional]
  B --> C[Extract_audio]
  C --> D[Transcribe_local_Whisper]
  D --> E{Transcript_and_caption_gates}
  E -->|ok_or_caption_primary| F[LLM_classify_entities_summary_title]
  F --> G[Optional_verify_and_rewrite]
  G --> H[Write_graph_notes_and_assets]
  E -->|blocked| I[Discord_Try_anyway]
```

For stage-by-stage detail, LLM labels, repair paths, and temp/idempotency behavior, see [architecture.md](architecture.md).

The diagram merges graph LLM steps into one node; the **`title`** completion runs **only** when `TITLE_STYLE=clean` (see [configuration.md](configuration.md#discrete-string-options)).
