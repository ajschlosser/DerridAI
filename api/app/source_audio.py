# Copyright 2026 Aaron John Schlosser, PhD.
"""Full-file OpenAI Whisper transcription and whisperx speaker spans."""

from __future__ import annotations

import importlib
import json
import math
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .source_kinds import AUDIO_SUFFIXES
from .source_safety import check_size, executable_version, tool_version
from .source_text import infer_initial_metadata

MAX_AUDIO_BYTES = 24 * 1024 * 1024
MAX_AUDIO_SECONDS = 4 * 3600


def probe_audio(path: Path) -> float:
    """Require bounded, local codec inspection before transmitting or decoding audio."""
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv, generated local path, no shell or network protocols
            [
                "ffprobe",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mp3,wav,mov,ogg,flac,matroska,webm,aac,mpeg",
                "-show_entries",
                "format=duration:stream=codec_type",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            timeout=15,
            check=True,
        )
        payload = json.loads(result.stdout)
        duration = float(payload["format"]["duration"])
        if not any(
            row.get("codec_type") == "audio" for row in payload.get("streams", [])
        ):
            raise ValueError("No supported audio stream.")
        if not math.isfinite(duration) or not 0 < duration <= MAX_AUDIO_SECONDS:
            raise ValueError("Audio duration exceeds supported limits.")
        return duration
    except FileNotFoundError as exc:
        raise ValueError(
            "Audio ingestion requires optional FFmpeg/ffprobe installation."
        ) from exc
    except (
        subprocess.SubprocessError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("Audio codec inspection failed.") from exc


def transcribe_entire_file(path: Path) -> dict[str, Any]:
    """Send the whole audio file to OpenAI Whisper before any span splitting."""
    from .system_store import system_store

    config = system_store.audio_transcription_settings(include_key=True)
    api_key = str(config.get("api_key") or "").strip()
    if not api_key:
        raise ValueError(
            "Audio transcription needs an API key. Add one under Settings → Providers → "
            "Audio transcription (or set OPENAI_API_KEY on the server)."
        )
    base = str(config["base_url"])
    model = str(config["model"])
    # Only segment timestamps are requested; HTTPX multipart expects a mapping.
    form = {
        "model": model,
        "response_format": "verbose_json",
        "timestamp_granularities[]": "segment",
    }
    try:
        with path.open("rb") as handle:
            response = httpx.post(
                f"{base}/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                data=form,
                files={"file": (path.name, handle, "application/octet-stream")},
                timeout=httpx.Timeout(600.0, connect=30.0),
            )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        raise ValueError(f"OpenAI Whisper transcription failed: {exc}") from exc
    if not isinstance(payload, dict) or not str(payload.get("text") or "").strip():
        raise ValueError("OpenAI Whisper returned an empty transcript.")
    return payload


def diarize_with_whisperx(path: Path) -> list[dict[str, Any]]:
    """Distinguish speakers with whisperx after the full-file transcript exists."""
    try:
        whisperx = importlib.import_module("whisperx")
    except ImportError as exc:
        raise RuntimeError(
            "whisperx is not installed; speaker diarization is unavailable."
        ) from exc
    audio = whisperx.load_audio(str(path))
    device = "cpu"
    try:
        torch = importlib.import_module("torch")
        if bool(torch.cuda.is_available()):
            device = "cuda"
    except Exception:
        device = "cpu"
    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or None
    try:
        pipeline = whisperx.DiarizationPipeline(device=device, use_auth_token=token)
    except TypeError:
        pipeline = whisperx.DiarizationPipeline(device=device, token=token)
    diarization = pipeline(audio)
    turns: list[dict[str, Any]] = []
    if hasattr(diarization, "iterrows"):
        for _, row in diarization.iterrows():
            speaker = str(row.get("speaker") or "").strip()
            if speaker:
                turns.append(
                    {
                        "start": float(row["start"]),
                        "end": float(row["end"]),
                        "speaker": speaker,
                    }
                )
    elif isinstance(diarization, list):
        for row in diarization:
            if not isinstance(row, dict):
                continue
            speaker = str(row.get("speaker") or "").strip()
            if speaker:
                turns.append(
                    {
                        "start": float(row.get("start") or 0),
                        "end": float(row.get("end") or 0),
                        "speaker": speaker,
                    }
                )
    return turns


def speaker_for_interval(
    start: float, end: float, turns: list[dict[str, Any]]
) -> str | None:
    """Choose the whisperx speaker whose turn overlaps this Whisper segment most.

    The transcript and the diarization are produced separately. Greatest overlap
    stays correct when a speaker turn straddles a segment boundary; nearest-start
    matching does not.
    """
    best: str | None = None
    best_overlap = 0.0
    for turn in turns:
        overlap = min(end, float(turn.get("end") or 0)) - max(
            start, float(turn.get("start") or 0)
        )
        if overlap > best_overlap:
            best_overlap = overlap
            best = str(turn.get("speaker") or "").strip() or None
    return best if best_overlap > 0 else None


def spans_from_transcript(
    transcript: dict[str, Any], turns: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Break a completed Whisper transcript into source spans, then label speakers."""
    segments = (
        transcript.get("segments")
        if isinstance(transcript.get("segments"), list)
        else []
    )
    blocks: list[dict[str, Any]] = []
    if not segments:
        raise ValueError("Transcript lacks required timestamped segments.")
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            continue
        value = str(segment.get("text") or "").strip()
        if not value:
            continue
        try:
            start = float(segment["start"])
            end = float(segment["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Transcript has invalid time ranges.") from exc
        if (
            not math.isfinite(start)
            or not math.isfinite(end)
            or not 0 <= start < end <= MAX_AUDIO_SECONDS
        ):
            raise ValueError("Transcript has invalid time ranges.")
        speaker = speaker_for_interval(start, end, turns)
        confidence = 0.8
        if segment.get("avg_logprob") is not None:
            try:
                confidence = max(
                    0.35, min(0.99, math.exp(float(segment["avg_logprob"])))
                )
            except (TypeError, ValueError, OverflowError):
                confidence = 0.8
        blocks.append(
            {
                "block_id": f"p{index:05d}-b0001",
                # Legacy navigation index only; never exported as an evidence page.
                "page": index,
                "locator_kind": "time",
                "bbox": [0, 0, 0, 0],
                "type": "paragraph",
                "text": value,
                "speaker": speaker,
                "start": round(start, 3),
                "end": round(end, 3),
                "time_label": _timestamp_label(start, end),
                "extraction_method": "whisper",
                "confidence": round(confidence, 3),
            }
        )
    original = " ".join(str(transcript.get("text") or "").split())
    segmented = " ".join(" ".join(block["text"] for block in blocks).split())
    if not blocks or original != segmented:
        raise ValueError("Transcript segments do not conserve the full transcription.")
    return blocks


def _timestamp_label(start: float, end: float) -> str:
    return f"{_clock(start)}–{_clock(end)}"


def _clock(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def extract_audio(
    data: bytes, *, filename: str, catalog: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Transcribe the whole recording before any source span is created.

    OpenAI Whisper must see the entire file first. whisperx then distinguishes
    speakers. Only after both results exist are timed spans written. A missing
    diarizer keeps the transcript and records a warning instead of dropping it.
    """
    check_size(data, MAX_AUDIO_BYTES)
    suffix = Path(filename).suffix.lower()
    if suffix not in AUDIO_SUFFIXES:
        raise ValueError("Unsupported audio format.")
    temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = Path(temp.name)
    warnings: list[str] = []
    try:
        temp.write(data)
        temp.close()
        duration = probe_audio(path)
        transcript = transcribe_entire_file(path)
        # Validate provider output before running the optional heavyweight diarizer.
        initial_spans = spans_from_transcript(transcript, [])
        if any(block["end"] > duration + 1 for block in initial_spans):
            raise ValueError("Transcript timestamps exceed the recording duration.")
        try:
            turns = diarize_with_whisperx(path)
        except Exception as exc:
            turns = []
            warnings.append(f"whisperx speaker diarization unavailable: {exc}")
        blocks = spans_from_transcript(transcript, turns)
        if not blocks:
            raise ValueError("OpenAI Whisper returned no source spans.")
        for block in blocks:
            if not block.get("speaker"):
                block.pop("speaker", None)
        pages = []
        for block in blocks:
            pages.append(
                {
                    "pdf_page": block["page"],
                    "locator_kind": "time",
                    "start": block["start"],
                    "end": block["end"],
                    "width": 0,
                    "height": 0,
                    "block_ids": [block["block_id"]],
                    "extraction_method": "whisper",
                }
            )
        embedded = (
            {"language": transcript.get("language")}
            if transcript.get("language")
            else {}
        )
        full_text = "\n\n".join(block["text"] for block in blocks)
        return {
            "filename": Path(filename).name,
            "page_count": len(pages),
            "metadata": embedded,
            "pages": pages,
            "blocks": blocks,
            "block_count": len(blocks),
            "included_block_count": len(blocks),
            "excluded_block_count": 0,
            "ocr_pages": 0,
            "warnings": warnings,
            "extractor": "openai-whisper+whisperx-v2",
            "source_transcription": transcript,
            "audio_provenance": {
                "model": os.getenv("OPENAI_WHISPER_MODEL", "whisper-1"),
                "provider": os.getenv(
                    "OPENAI_WHISPER_BASE_URL", "https://api.openai.com/v1"
                ),
                "httpx_version": tool_version("httpx"),
                "ffprobe_version": executable_version("ffprobe"),
                "whisperx_version": tool_version("whisperx"),
                "diarization_status": "failed"
                if warnings
                else "complete"
                if turns
                else "no_speakers",
                "duration_seconds": duration,
            },
            "media_kind": "audio",
            "initial_metadata": infer_initial_metadata(
                full_text, embedded=embedded, blocks=blocks, catalog=catalog
            ),
        }
    finally:
        temp.close()
        path.unlink(missing_ok=True)
