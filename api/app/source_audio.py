# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Audio transcription, word alignment, diarization, and timed speaker spans."""

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
SPEAKER_AMBIGUITY_MARGIN = 0.15
SPEAKER_TURN_GAP_SECONDS = 1.25


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
        raise ValueError("Audio ingestion requires FFmpeg/ffprobe.") from exc
    except (
        subprocess.SubprocessError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("Audio codec inspection failed.") from exc


def transcribe_entire_file(path: Path) -> dict[str, Any]:
    """Transcribe the whole file and request both segment and word timestamps."""
    from .source_identity import CaptureError, CaptureErrorCode
    from .system_store import system_store

    config = system_store.audio_transcription_settings(include_key=True)
    api_key = str(config.get("api_key") or "").strip()
    if not api_key:
        raise CaptureError(
            CaptureErrorCode.AUDIO_PROVIDER_NOT_CONFIGURED,
            "Audio transcription needs an API key. Add one under Settings → Providers → "
            "Audio transcription (or set OPENAI_API_KEY on the server).",
        )
    base = str(config["base_url"])
    model = str(config["model"])
    # Multipart form data is a sequence so the timestamp key can be repeated.
    # OpenAI-compatible providers that support verbose timestamps return both
    # segment boundaries and word boundaries from this request.
    form = [
        ("model", model),
        ("response_format", "verbose_json"),
        ("timestamp_granularities[]", "segment"),
        ("timestamp_granularities[]", "word"),
    ]
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
    except httpx.HTTPStatusError as exc:
        code = (
            CaptureErrorCode.AUDIO_PROVIDER_UNAVAILABLE
            if exc.response.status_code >= 500
            else CaptureErrorCode.AUDIO_TRANSCRIPTION_FAILED
        )
        raise CaptureError(
            code,
            "Audio transcription provider rejected the request.",
            detail=f"HTTP {exc.response.status_code}",
        ) from exc
    except (httpx.HTTPError, OSError) as exc:
        raise CaptureError(
            CaptureErrorCode.AUDIO_PROVIDER_UNAVAILABLE,
            "Audio transcription failed because the provider could not be reached.",
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise CaptureError(
            CaptureErrorCode.AUDIO_TRANSCRIPTION_FAILED,
            "Audio transcription failed.",
            detail=str(exc),
        ) from exc
    if not isinstance(payload, dict) or not str(payload.get("text") or "").strip():
        raise CaptureError(
            CaptureErrorCode.AUDIO_TRANSCRIPTION_FAILED,
            "Audio transcription returned no text.",
        )
    return payload


def _whisperx_device() -> str:
    """Use CUDA when available while keeping one device decision for all WhisperX work."""
    try:
        torch = importlib.import_module("torch")
        if bool(torch.cuda.is_available()):
            return "cuda"
    except Exception:
        pass
    return "cpu"


def _load_whisperx() -> Any:
    try:
        return importlib.import_module("whisperx")
    except ImportError as exc:
        raise RuntimeError("whisperx is not installed.") from exc


def _valid_timed_word(value: Any) -> bool:
    if not isinstance(value, dict) or not str(value.get("word") or "").strip():
        return False
    try:
        start = float(value["start"])
        end = float(value["end"])
    except (KeyError, TypeError, ValueError):
        return False
    return math.isfinite(start) and math.isfinite(end) and 0 <= start < end <= MAX_AUDIO_SECONDS


def transcript_words(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    """Return all valid timed words supplied by the provider or WhisperX alignment."""
    top_level = transcript.get("words")
    if isinstance(top_level, list):
        words = [dict(word) for word in top_level if _valid_timed_word(word)]
        if words:
            return words

    words: list[dict[str, Any]] = []
    segments = transcript.get("segments")
    if not isinstance(segments, list):
        return words
    for segment in segments:
        if not isinstance(segment, dict) or not isinstance(segment.get("words"), list):
            continue
        words.extend(dict(word) for word in segment["words"] if _valid_timed_word(word))
    return words


def align_transcript_with_whisperx(
    path: Path, transcript: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    """Add word timestamps when the transcription provider returned only segments.

    The provider transcript remains authoritative text. WhisperX contributes timing
    only: the original segments are retained and aligned words are attached at the
    top level so downstream speaker assignment can operate at word resolution.
    """
    if transcript_words(transcript):
        return transcript, "provider_word_timestamps"

    segments = transcript.get("segments")
    language = str(transcript.get("language") or "").strip()
    if not isinstance(segments, list) or not segments or not language:
        raise RuntimeError("WhisperX alignment needs timestamped segments and a language.")

    whisperx = _load_whisperx()
    device = _whisperx_device()
    audio = whisperx.load_audio(str(path))
    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    try:
        aligned = whisperx.align(
            segments,
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )
    except TypeError:
        aligned = whisperx.align(segments, align_model, metadata, audio, device)

    aligned_words: list[dict[str, Any]] = []
    if isinstance(aligned, dict):
        word_segments = aligned.get("word_segments")
        if isinstance(word_segments, list):
            aligned_words = [
                dict(word) for word in word_segments if _valid_timed_word(word)
            ]
        if not aligned_words and isinstance(aligned.get("segments"), list):
            for segment in aligned["segments"]:
                if isinstance(segment, dict) and isinstance(segment.get("words"), list):
                    aligned_words.extend(
                        dict(word) for word in segment["words"] if _valid_timed_word(word)
                    )
    if not aligned_words:
        raise RuntimeError("WhisperX alignment returned no timed words.")

    enriched = dict(transcript)
    enriched["words"] = aligned_words
    return enriched, "whisperx_word_alignment"


def diarize_with_whisperx(path: Path) -> list[dict[str, Any]]:
    """Distinguish speaker turns while retaining the diarizer's original labels."""
    whisperx = _load_whisperx()
    audio = whisperx.load_audio(str(path))
    device = _whisperx_device()
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
    return normalize_speaker_labels(turns)


def normalize_speaker_labels(turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map provider voice clusters to stable SPEAKER_n identities by first appearance."""
    labels: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    for turn in sorted(turns, key=lambda item: float(item.get("start") or 0)):
        provider_label = str(turn.get("speaker") or "").strip()
        if not provider_label:
            continue
        label = labels.setdefault(provider_label, f"SPEAKER_{len(labels) + 1}")
        normalized.append(
            {
                **turn,
                "speaker": label,
                "provider_speaker": str(
                    turn.get("provider_speaker") or provider_label
                ),
            }
        )
    return normalized


def _speaker_overlap_candidates(
    start: float, end: float, turns: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return positive speaker overlaps ordered from strongest to weakest."""
    candidates: list[dict[str, Any]] = []
    for turn in turns:
        turn_start = float(turn.get("start") or 0)
        turn_end = float(turn.get("end") or 0)
        overlap = min(end, turn_end) - max(start, turn_start)
        speaker = str(turn.get("speaker") or "").strip()
        if overlap <= 0 or not speaker:
            continue
        candidates.append(
            {
                "speaker": speaker,
                "provider_speaker": str(
                    turn.get("provider_speaker") or speaker
                ),
                "overlap": overlap,
            }
        )
    return sorted(candidates, key=lambda item: float(item["overlap"]), reverse=True)


def speaker_assignment_for_interval(
    start: float, end: float, turns: list[dict[str, Any]]
) -> dict[str, Any]:
    """Describe the strongest speaker assignment and its temporal uncertainty."""
    candidates = _speaker_overlap_candidates(start, end, turns)
    duration = max(end - start, 0.001)
    if not candidates:
        return {
            "speaker": None,
            "provider_speaker": None,
            "confidence": 0.0,
            "ambiguous": False,
        }

    best = candidates[0]
    best_overlap = float(best["overlap"])
    second_overlap = float(candidates[1]["overlap"]) if len(candidates) > 1 else 0.0
    confidence = max(0.0, min(1.0, best_overlap / duration))
    ambiguity_gap = (best_overlap - second_overlap) / duration
    return {
        "speaker": best["speaker"],
        "provider_speaker": best["provider_speaker"],
        "confidence": round(confidence, 3),
        "ambiguous": len(candidates) > 1 and ambiguity_gap < SPEAKER_AMBIGUITY_MARGIN,
    }


def speaker_for_interval(
    start: float, end: float, turns: list[dict[str, Any]]
) -> str | None:
    """Compatibility helper returning only the strongest overlapping speaker."""
    value = speaker_assignment_for_interval(start, end, turns)
    return str(value["speaker"]) if value.get("speaker") else None


def _segment_confidence(segment: dict[str, Any]) -> float:
    confidence = 0.8
    if segment.get("avg_logprob") is not None:
        try:
            confidence = max(
                0.35, min(0.99, math.exp(float(segment["avg_logprob"])))
            )
        except (TypeError, ValueError, OverflowError):
            pass
    return round(confidence, 3)


def _words_for_segment(
    segment: dict[str, Any], words: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    start = float(segment["start"])
    end = float(segment["end"])
    selected: list[dict[str, Any]] = []
    for word in words:
        word_start = float(word["start"])
        word_end = float(word["end"])
        midpoint = word_start + (word_end - word_start) / 2
        if start - 0.05 <= midpoint <= end + 0.05:
            selected.append(dict(word))
    return selected


def _word_offsets(text: str, words: list[dict[str, Any]]) -> list[tuple[int, int]] | None:
    """Map timed word strings back onto the provider's exact segment text.

    Blocks are sliced from the original segment string rather than rebuilt from
    token text, preserving punctuation and whitespace while still allowing a
    speaker transition inside a transcription segment.
    """
    cursor = 0
    offsets: list[tuple[int, int]] = []
    folded = text.casefold()
    for word in words:
        token = str(word.get("word") or "").strip()
        if not token:
            return None
        position = text.find(token, cursor)
        if position < 0:
            position = folded.find(token.casefold(), cursor)
        if position < 0:
            return None
        offsets.append((position, position + len(token)))
        cursor = position + len(token)
    return offsets


def _speaker_word_groups(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = []
    for word in words:
        if not groups:
            groups.append([word])
            continue
        previous = groups[-1][-1]
        same_speaker = previous.get("speaker") == word.get("speaker")
        gap = float(word["start"]) - float(previous["end"])
        if same_speaker and gap <= SPEAKER_TURN_GAP_SECONDS:
            groups[-1].append(word)
        else:
            groups.append([word])
    return groups


def _word_level_segment_blocks(
    segment: dict[str, Any],
    words: list[dict[str, Any]],
    turns: list[dict[str, Any]],
    segment_index: int,
) -> list[dict[str, Any]] | None:
    text = str(segment.get("text") or "").strip()
    offsets = _word_offsets(text, words)
    if not text or not offsets or len(offsets) != len(words):
        return None

    assigned_words: list[dict[str, Any]] = []
    for word in words:
        assignment = speaker_assignment_for_interval(
            float(word["start"]), float(word["end"]), turns
        )
        assigned_words.append(
            {
                "word": str(word.get("word") or ""),
                "start": round(float(word["start"]), 3),
                "end": round(float(word["end"]), 3),
                "speaker": assignment["speaker"],
                "provider_speaker": assignment["provider_speaker"],
                "speaker_confidence": assignment["confidence"],
                "speaker_ambiguous": assignment["ambiguous"],
                **(
                    {"score": word.get("score")}
                    if word.get("score") is not None
                    else {}
                ),
            }
        )

    groups = _speaker_word_groups(assigned_words)
    word_index = 0
    blocks: list[dict[str, Any]] = []
    for group_index, group in enumerate(groups, 1):
        group_start_word = word_index
        word_index += len(group)
        char_start = 0 if group_index == 1 else offsets[group_start_word][0]
        char_end = len(text) if word_index == len(words) else offsets[word_index][0]
        value = text[char_start:char_end].strip()
        if not value:
            continue

        start = float(group[0]["start"])
        end = float(group[-1]["end"])
        speaker = group[0].get("speaker")
        provider_speaker = group[0].get("provider_speaker")
        speaker_confidences = [
            float(item["speaker_confidence"])
            for item in group
            if item.get("speaker") is not None
        ]
        ambiguous_count = sum(bool(item["speaker_ambiguous"]) for item in group)
        block = {
            "block_id": f"p{segment_index:05d}-b{group_index:04d}",
            "locator_kind": "time",
            "bbox": [0, 0, 0, 0],
            "type": "paragraph",
            "text": value,
            "start": round(start, 3),
            "end": round(end, 3),
            "time_label": _timestamp_label(start, end),
            "extraction_method": "whisper+word-speaker-alignment",
            "confidence": _segment_confidence(segment),
            "source_words": group,
            "speaker_assignment": {
                "method": "word_overlap",
                "confidence": round(
                    sum(speaker_confidences) / len(speaker_confidences), 3
                )
                if speaker_confidences
                else 0.0,
                "ambiguous_word_count": ambiguous_count,
                "word_count": len(group),
                "review_recommended": ambiguous_count > 0 or speaker is None,
            },
        }
        if speaker:
            block["speaker"] = speaker
        if provider_speaker:
            block["provider_speaker"] = provider_speaker
        blocks.append(block)
    return blocks or None


def _segment_level_block(
    segment: dict[str, Any],
    turns: list[dict[str, Any]],
    segment_index: int,
) -> dict[str, Any]:
    value = str(segment.get("text") or "").strip()
    start = float(segment["start"])
    end = float(segment["end"])
    assignment = speaker_assignment_for_interval(start, end, turns)
    block: dict[str, Any] = {
        "block_id": f"p{segment_index:05d}-b0001",
        "locator_kind": "time",
        "bbox": [0, 0, 0, 0],
        "type": "paragraph",
        "text": value,
        "start": round(start, 3),
        "end": round(end, 3),
        "time_label": _timestamp_label(start, end),
        "extraction_method": "whisper",
        "confidence": _segment_confidence(segment),
    }
    if assignment.get("speaker"):
        block["speaker"] = assignment["speaker"]
        block["provider_speaker"] = assignment["provider_speaker"]
        block["speaker_assignment"] = {
            "method": "segment_overlap",
            "confidence": assignment["confidence"],
            "ambiguous_word_count": 0,
            "word_count": 0,
            "review_recommended": bool(assignment["ambiguous"]),
        }
    return block


def _validate_segment_time(segment: dict[str, Any]) -> tuple[float, float]:
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
    return start, end


def spans_from_transcript(
    transcript: dict[str, Any], turns: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build exact-text timed spans, splitting inside segments at speaker changes."""
    segments = (
        transcript.get("segments")
        if isinstance(transcript.get("segments"), list)
        else []
    )
    if not segments:
        raise ValueError("Transcript lacks required timestamped segments.")

    words = transcript_words(transcript)
    blocks: list[dict[str, Any]] = []
    for segment_index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            continue
        value = str(segment.get("text") or "").strip()
        if not value:
            continue
        _validate_segment_time(segment)

        segment_words = _words_for_segment(segment, words) if words and turns else []
        word_blocks = (
            _word_level_segment_blocks(
                segment, segment_words, turns, segment_index
            )
            if segment_words
            else None
        )
        if word_blocks:
            blocks.extend(word_blocks)
        else:
            blocks.append(_segment_level_block(segment, turns, segment_index))

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


def _audio_service_provenance() -> dict[str, str]:
    """Persist the configured transcription endpoint/model, never its credential."""
    from .system_store import system_store

    config = system_store.audio_transcription_settings(include_key=False)
    return {
        "model": str(config.get("model") or "whisper-1"),
        "provider": str(config.get("base_url") or "https://api.openai.com/v1"),
    }


def _speaker_assignment_summary(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    assignments = [
        block.get("speaker_assignment")
        for block in blocks
        if isinstance(block.get("speaker_assignment"), dict)
    ]
    word_level = [
        assignment
        for assignment in assignments
        if assignment.get("method") == "word_overlap"
    ]
    ambiguous_words = sum(
        int(assignment.get("ambiguous_word_count") or 0) for assignment in assignments
    )
    word_count = sum(int(assignment.get("word_count") or 0) for assignment in assignments)
    review_blocks = sum(bool(assignment.get("review_recommended")) for assignment in assignments)
    return {
        "method": "word_overlap"
        if word_level
        else "segment_overlap"
        if assignments
        else "none",
        "word_count": word_count,
        "ambiguous_word_count": ambiguous_words,
        "review_recommended_block_count": review_blocks,
    }


def extract_audio(
    data: bytes,
    *,
    filename: str,
    catalog: dict[str, Any] | None = None,
    diarize: bool = True,
) -> dict[str, Any]:
    """Run transcription, word alignment, diarization, and speaker-turn reconstruction."""
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

        # Validate provider segment timing before additional inference. This also
        # proves that the provider transcript conserves its own segment text.
        initial_spans = spans_from_transcript(transcript, [])
        if any(block["end"] > duration + 1 for block in initial_spans):
            raise ValueError("Transcript timestamps exceed the recording duration.")

        turns: list[dict[str, Any]] = []
        alignment_status = "not_requested"
        enriched_transcript = transcript
        if diarize:
            try:
                turns = diarize_with_whisperx(path)
            except Exception as exc:
                warnings.append(f"whisperx speaker diarization unavailable: {exc}")
            if turns:
                try:
                    enriched_transcript, alignment_status = align_transcript_with_whisperx(
                        path, transcript
                    )
                except Exception as exc:
                    alignment_status = "failed"
                    warnings.append(
                        "whisperx word alignment unavailable; "
                        f"speaker assignment fell back to transcript segments: {exc}"
                    )
            else:
                alignment_status = "not_applicable"
        else:
            alignment_status = "disabled"

        blocks = spans_from_transcript(enriched_transcript, turns)
        if not blocks:
            raise ValueError("OpenAI Whisper returned no source spans.")

        embedded = (
            {"language": transcript.get("language")}
            if transcript.get("language")
            else {}
        )
        full_text = "\n\n".join(block["text"] for block in blocks)
        assignment = _speaker_assignment_summary(blocks)
        diarization_status = (
            "disabled"
            if not diarize
            else "failed"
            if not turns and warnings
            else "complete"
            if turns
            else "no_speakers"
        )
        return {
            "filename": Path(filename).name,
            # Audio evidence uses time locators. Page semantics stay absent so
            # downstream citations cannot accidentally render fabricated pages.
            "page_count": 0,
            "metadata": embedded,
            "pages": [],
            "blocks": blocks,
            "block_count": len(blocks),
            "included_block_count": len(blocks),
            "excluded_block_count": 0,
            "ocr_pages": 0,
            "warnings": warnings,
            "extractor": "openai-whisper+whisperx-v3",
            # Preserve provider output and normalized diarization independently of
            # later human transcript/speaker review.
            "source_transcription": transcript,
            "source_diarization": turns,
            "audio_provenance": {
                **_audio_service_provenance(),
                "httpx_version": tool_version("httpx"),
                "ffprobe_version": executable_version("ffprobe"),
                "whisperx_version": tool_version("whisperx"),
                "diarization_requested": diarize,
                "diarization_status": diarization_status,
                "alignment_status": alignment_status,
                "speaker_assignment_method": assignment["method"],
                "word_count": assignment["word_count"],
                "ambiguous_word_count": assignment["ambiguous_word_count"],
                "review_recommended_block_count": assignment[
                    "review_recommended_block_count"
                ],
                "voice_labels": {
                    str(turn["speaker"]): str(
                        turn.get("provider_speaker") or turn["speaker"]
                    )
                    for turn in turns
                    if turn.get("speaker")
                },
                "duration_seconds": duration,
                "pipeline_stages": {
                    "probe": "complete",
                    "transcription": "complete",
                    "alignment": alignment_status,
                    "diarization": diarization_status,
                    "speaker_assignment": assignment["method"],
                    "turn_reconstruction": "complete",
                },
            },
            "media_kind": "audio",
            "initial_metadata": infer_initial_metadata(
                full_text, embedded=embedded, blocks=blocks, catalog=catalog
            ),
        }
    finally:
        temp.close()
        path.unlink(missing_ok=True)
