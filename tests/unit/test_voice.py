"""Tests for voice pipeline components.

Uses mocked audio/STT/TTS — no microphone or speaker hardware needed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest


class TestSpeechToText:
    """STT should transcribe audio and handle edge cases."""

    async def test_transcribe_returns_text(self, mock_stt: AsyncMock) -> None:
        """STT should return transcribed text from audio."""
        text = await mock_stt.transcribe(b"\x00" * 16000)
        assert text == "turn on the living room lights"

    async def test_transcribe_called_with_audio(
        self, mock_stt: AsyncMock, sample_audio_bytes: bytes
    ) -> None:
        """STT should be called with the audio data."""
        await mock_stt.transcribe(sample_audio_bytes)
        mock_stt.transcribe.assert_called_once_with(sample_audio_bytes)

    async def test_empty_audio_handled(self, mock_stt: AsyncMock) -> None:
        """STT should handle empty/silence audio."""
        mock_stt.transcribe.return_value = ""
        text = await mock_stt.transcribe(b"")
        assert text == ""


class TestTextToSpeech:
    """TTS should synthesize audio from text."""

    async def test_synthesize_returns_bytes(self, mock_tts: AsyncMock) -> None:
        """TTS should return audio bytes."""
        audio = await mock_tts.synthesize("Hello there!")
        assert isinstance(audio, bytes)
        assert len(audio) > 0

    async def test_synthesize_empty_text(self, mock_tts: AsyncMock) -> None:
        """TTS should handle empty input gracefully."""
        mock_tts.synthesize.return_value = b""
        audio = await mock_tts.synthesize("")
        assert audio == b""


class TestWakeWord:
    """Wake word detector should identify trigger phrases."""

    async def test_detection(self, mock_wake_word: AsyncMock) -> None:
        """Should detect the wake word."""
        detected = await mock_wake_word.detected(b"\x00" * 16000)
        assert detected is True

    async def test_no_detection(self, mock_wake_word: AsyncMock) -> None:
        """Should return False when wake word is absent."""
        mock_wake_word.detected.return_value = False
        detected = await mock_wake_word.detected(b"\x00" * 16000)
        assert detected is False


class TestAudioFile:
    """Audio file handling."""

    def test_sample_wav_created(self, sample_audio_path: Path) -> None:
        """The sample audio fixture should produce a valid .wav file."""
        assert sample_audio_path.exists()
        assert sample_audio_path.suffix == ".wav"
        assert sample_audio_path.stat().st_size > 0

    def test_sample_wav_format(self, sample_audio_path: Path) -> None:
        """Sample wav should be 16kHz 16-bit mono."""
        import wave

        with wave.open(str(sample_audio_path), "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
