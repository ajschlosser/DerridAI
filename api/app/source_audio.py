# Copyright 2026 Aaron John Schlosser, PhD.
"""Full-file OpenAI Whisper transcription and whisperx speaker spans."""
from __future__ import annotations

import importlib
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .source_kinds import AUDIO_SUFFIXES
from .source_text import infer_initial_metadata

def transcribe_entire_file(path: Path) -> dict[str, Any]:
    """Send the whole audio file to OpenAI Whisper before any span splitting."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or settings.openai_compat_api_key.strip()
    if not api_key:
        raise ValueError("OpenAI Whisper requires OPENAI_API_KEY.")
    base = os.getenv("OPENAI_WHISPER_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")
    # Repeated form keys ask Whisper for segment timestamps. A dict cannot
    # repeat timestamp_granularities[], so this stays a list of pairs.
    form: Any = [
        ("model", model),
        ("response_format", "verbose_json"),
        ("timestamp_granularities[]", "segment"),
    ]
    with path.open("rb") as handle:
        response = httpx.post(
            f"{base}/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data=form,
            files={"file": (path.name, handle, "application/octet-stream")},
            timeout=httpx.Timeout(600.0, connect=30.0),
        )
    try:
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
        raise RuntimeError("whisperx is not installed; speaker diarization is unavailable.") from exc
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
                turns.append({"start": float(row["start"]), "end": float(row["end"]), "speaker": speaker})
    elif isinstance(diarization, list):
        for row in diarization:
            if not isinstance(row, dict):
                continue
            speaker = str(row.get("speaker") or "").strip()
            if speaker:
                turns.append({"start": float(row.get("start") or 0), "end": float(row.get("end") or 0), "speaker": speaker})
    return turns


def speaker_for_interval(start: float, end: float, turns: list[dict[str, Any]]) -> str | None:
    """Choose the whisperx speaker whose turn overlaps this Whisper segment most.

    The transcript and the diarization are produced separately. Greatest overlap
    stays correct when a speaker turn straddles a segment boundary; nearest-start
    matching does not.
    """
    best: str | None = None
    best_overlap = 0.0
    for turn in turns:
        overlap = min(end, float(turn.get("end") or 0)) - max(start, float(turn.get("start") or 0))
        if overlap > best_overlap:
            best_overlap = overlap
            best = str(turn.get("speaker") or "").strip() or None
    return best if best_overlap > 0 else None


def spans_from_transcript(transcript: dict[str, Any], turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Break a completed Whisper transcript into source spans, then label speakers."""
    segments = transcript.get("segments") if isinstance(transcript.get("segments"), list) else []
    blocks: list[dict[str, Any]] = []
    if not segments:
        text = str(transcript.get("text") or "").strip()
        if text:
            segments = [{"start": 0, "end": 0, "text": text}]
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            continue
        value = str(segment.get("text") or "").strip()
        if not value:
            continue
        start = float(segment.get("start") or 0)
        end = float(segment.get("end") or start)
        speaker = speaker_for_interval(start, end, turns)
        confidence = 0.8
        if segment.get("avg_logprob") is not None:
            try:
                confidence = max(0.35, min(0.99, math.exp(float(segment["avg_logprob"]))))
            except (TypeError, ValueError, OverflowError):
                confidence = 0.8
        blocks.append({
            "block_id": f"p{index:05d}-b0001",
            "page": index,
            "bbox": [0, 0, 0, 0],
            "type": "paragraph",
            "text": value,
            "speaker": speaker,
            "start": round(start, 3),
            "end": round(end, 3),
            "printed_page_label": _timestamp_label(start, end),
            "printed_page_label_source": "whisper_timestamp",
            "extraction_method": "whisper",
            "confidence": round(confidence, 3),
        })
    return blocks


def _timestamp_label(start: float, end: float) -> str:
    return f"{_clock(start)}–{_clock(end)}"


def _clock(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def extract_audio(data: bytes, *, filename: str, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    """Transcribe the whole recording before any source span is created.

    OpenAI Whisper must see the entire file first. whisperx then distinguishes
    speakers. Only after both results exist are timed spans written. A missing
    diarizer keeps the transcript and records a warning instead of dropping it.
    """
    suffix = Path(filename).suffix.lower() if Path(filename).suffix.lower() in AUDIO_SUFFIXES else ".audio"
    temp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = Path(temp.name)
    warnings: list[str] = []
    try:
        temp.write(data)
        temp.close()
        transcript = transcribe_entire_file(path)
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
            pages.append({
                "pdf_page": block["page"],
                "printed_page_label": block.get("printed_page_label"),
                "printed_page_label_source": "whisper_timestamp",
                "width": 0,
                "height": 0,
                "block_ids": [block["block_id"]],
                "extraction_method": "whisper",
            })
        embedded = {"language": transcript.get("language")} if transcript.get("language") else {}
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
            "extractor": "openai-whisper+whisperx-v1",
            "media_kind": "audio",
            "initial_metadata": infer_initial_metadata(full_text, embedded=embedded, blocks=blocks, catalog=catalog),
        }
    finally:
        path.unlink(missing_ok=True)

