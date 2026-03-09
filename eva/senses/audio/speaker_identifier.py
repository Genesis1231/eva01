"""
SpeakerIdentifier — EVA's voice recognition.

Matches speech audio to known voice embeddings using pyannote/wespeaker.
Mirror of eva/senses/vision/identifier.py for the audio domain.
"""

import hashlib
import pickle
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import torch
from scipy.spatial.distance import cosine
from silero_vad import load_silero_vad, get_speech_timestamps

from config import logger, DATA_DIR
from eva.core.people import PeopleDB


class SpeakerIdentifier:
    """Matches speech to known people by voice embedding similarity."""

    _MODEL_ID = "pyannote/wespeaker-voxceleb-resnet34-LM"
    _VOICE_DIR = DATA_DIR / "voices"
    _CERTAIN_THRESHOLD = 0.30   # cosine distance — below = confident match
    _LIKELY_THRESHOLD = 0.50    # below = likely match
    _MIN_AUDIO_SECONDS = 0.5
    _SAMPLE_RATE = 16000

    def __init__(self, people_db: PeopleDB):
        self._people_lookup: Dict[str, str] = people_db.get_id_name_map()
        self._cache_path = self._VOICE_DIR / ".embeddings_cache.pkl"
        self._inference = None
        self._vad_model = None
        self._initialized = False
        
        self._ref_embeddings: Dict[str, np.ndarray] = {}

    def init_model(self) -> None:
        """Initialize speaker-identification dependencies once."""
        if self._initialized:
            return

        self._init_model()
        self._init_vad()
        self._load_reference_embeddings()
        self._initialized = True

    def _init_model(self) -> None:
        self._VOICE_DIR.mkdir(parents=True, exist_ok=True)
        try:
            from pyannote.audio import Model, Inference

            model = Model.from_pretrained(self._MODEL_ID)
            if model is None:
                raise RuntimeError("pyannote model returned None")
            self._inference = Inference(model, window="whole")
            logger.debug(f"SpeakerIdentifier: Loaded {self._MODEL_ID}.")
        except Exception as e:
            logger.warning(f"SpeakerIdentifier: Failed to load model — {e}")

    def _init_vad(self) -> None:
        try:
            self._vad_model = load_silero_vad()
            logger.debug("SpeakerIdentifier: Silero VAD loaded.")
        except Exception as e:
            logger.warning(f"SpeakerIdentifier: VAD unavailable — {e}")

    def _trim_silence(self, audio: np.ndarray) -> np.ndarray:
        """Strip leading/trailing silence using Silero VAD."""
        if self._vad_model is None:
            return audio

        tensor = torch.from_numpy(audio).float()
        stamps = get_speech_timestamps(tensor, self._vad_model, sampling_rate=self._SAMPLE_RATE)
        self._vad_model.reset_states()

        if not stamps:
            return audio

        pad = self._SAMPLE_RATE // 10  # 100ms padding
        start = max(0, stamps[0]["start"] - pad)
        end = min(len(audio), stamps[-1]["end"] + pad)
        return audio[start:end]

    def _load_reference_embeddings(self) -> None:
        if self._inference is None:
            return

        # Scan voice samples: data/voices/{person_id}/*.wav
        voice_files: Dict[str, list[Path]] = {}
        for person_dir in self._VOICE_DIR.iterdir():
            if not person_dir.is_dir() or person_dir.name.startswith("."):
                continue
            wavs = sorted(person_dir.glob("*.wav"))
            if wavs:
                voice_files[person_dir.name] = wavs

        if not voice_files:
            logger.debug("SpeakerIdentifier: No voice samples found.")
            return

        # Check cache validity via file fingerprint (paths + mtimes)
        fingerprint = self._compute_fingerprint(voice_files)
        if self._cache_path.exists():
            try:
                with open(self._cache_path, "rb") as f:
                    cached = pickle.load(f)
                if cached.get("fingerprint") == fingerprint:
                    self._ref_embeddings = cached["embeddings"]
                    logger.debug(
                        f"SpeakerIdentifier: Loaded {len(self._ref_embeddings)} voices from cache."
                    )
                    return
            except Exception:
                pass

        # Compute fresh embeddings
        logger.debug("SpeakerIdentifier: Computing voice embeddings...")
        for person_id, wavs in voice_files.items():
            embeddings = []
            for wav in wavs:
                try:
                    emb = self._inference(str(wav))
                    embeddings.append(emb)
                except Exception as e:
                    logger.warning(f"SpeakerIdentifier: Failed on {wav.name} — {e}")
            if embeddings:
                self._ref_embeddings[person_id] = np.mean(embeddings, axis=0)

        # Save cache
        try:
            with open(self._cache_path, "wb") as f:
                pickle.dump(
                    {"fingerprint": fingerprint, "embeddings": self._ref_embeddings}, f
                )
        except Exception as e:
            logger.warning(f"SpeakerIdentifier: Failed to save cache — {e}")

        logger.debug(
            f"SpeakerIdentifier: Loaded {len(self._ref_embeddings)} known voices."
        )

    @staticmethod
    def _compute_fingerprint(voice_files: Dict[str, list[Path]]) -> str:
        h = hashlib.md5()
        for person_id in sorted(voice_files):
            for wav in voice_files[person_id]:
                h.update(f"{wav}:{wav.stat().st_mtime}".encode())
        return h.hexdigest()

    def identify(self, audio: np.ndarray) -> Optional[Dict]:
        """Identify who is speaking from raw 16kHz mono float32 audio.

        Returns:
            {"id": person_id, "name": name} on match, None otherwise.
        """
        if not self._initialized:
            self.init_model()

        if self._inference is None or not self._ref_embeddings:
            return None

        audio = self._trim_silence(audio)
        if len(audio) < self._SAMPLE_RATE * self._MIN_AUDIO_SECONDS:
            return None

        try:
            waveform = audio.reshape(1, -1)
            embedding = self._inference(
                {"waveform": torch.from_numpy(waveform), "sample_rate": self._SAMPLE_RATE}
            )
        except Exception as e:
            logger.warning(f"SpeakerIdentifier: Embedding failed — {e}")
            return None

        # Find closest reference
        best_id = None
        best_dist = float("inf")
        for person_id, ref_emb in self._ref_embeddings.items():
            dist = cosine(embedding, ref_emb)
            if dist < best_dist:
                best_dist = dist
                best_id = person_id

        name = self._people_lookup.get(best_id) if best_id else None
        if not name:
            return None

        if best_dist <= self._CERTAIN_THRESHOLD:
            return {"id": best_id, "name": name}

        if best_dist <= self._LIKELY_THRESHOLD:
            return {"id": best_id, "name": f"Someone sounds like {name}"}

        return None

    def close(self) -> None:
        self._people_lookup.clear()
        self._ref_embeddings.clear()
        self._inference = None
        self._vad_model = None
        logger.debug("SpeakerIdentifier: Released.")
