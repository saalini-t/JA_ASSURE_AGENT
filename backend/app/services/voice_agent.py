"""
Voice Agent - Input Handling & Voice-Ready Script Formatter.
Part of the JA Assure Voice Agent layer (Abhi Ram's contribution).

Focuses on the input/handling side: turning script text from the Content Agent
into a clean, natural voice-ready format before passing to speech synthesis (gTTS).

Workflow:
Content Agent produces script -> Voice Agent prepares & formats it -> gTTS generates audio -> video assembly step.
"""

import re
import logging
from typing import List, Optional, Dict
from app.schemas.agent_contracts import VideoScript, VideoScene, VoiceGenerationResult

logger = logging.getLogger("ja_assure.voice_agent")


# Acronyms pronounced letter-by-letter in Southeast Asian financial/insurance context
ACRONYM_PRONUNCIATION_MAP: Dict[str, str] = {
    r"\bMAS\b": "M-A-S",
    r"\bPDPA\b": "P-D-P-A",
    r"\bMOH\b": "M-O-H",
    r"\bAI\b": "A-I",
    r"\bB2B\b": "B-to-B",
    r"\bB2C\b": "B-to-C",
    r"\bAPI\b": "A-P-I",
    r"\bSLA\b": "S-L-A",
    r"\bKYC\b": "K-Y-C",
    r"\bAML\b": "A-M-L",
    r"\bUGC\b": "U-G-C",
    r"\bSME\b": "S-M-E",
    r"\bSMEs\b": "S-M-Es",
}

# Common conversational and document abbreviations
ABBREVIATION_MAP: Dict[str, str] = {
    r"\be\.g\.,?\s*": "for example, ",
    r"\bi\.e\.,?\s*": "that is, ",
    r"\betc\b\.?": "and so forth",
    r"\bvs\.?\b": "versus",
    r"\bdept\.?\b": "department",
    r"\bapprox\.?\b": "approximately",
}


def clean_voiceover_text(text: str) -> str:
    """
    Transform raw script or storyboard copy into a clean voice-ready format:
    1. Strip visual stage cues and bracketed directions (e.g. [Visual: ...], (smiling), (voiceover:)).
    2. Strip markdown headers, bold, italics, links, and bullet markers.
    3. Normalize regional currency expressions (S$, RM, HK$, USD).
    4. Normalize abbreviations and regional regulatory/insurance acronyms for natural gTTS delivery.
    5. Clean punctuation cadence for optimal text-to-speech pauses.
    """
    if not text:
        return ""

    s = text.strip()

    # 1. Remove bracketed stage directions, visuals, and audio cues
    # [Visual: ...], [Scene 1], [B-roll ...], [Music swells], (voiceover:), (smiling), etc.
    s = re.sub(r"\[(?:visual|scene|b-roll|music|sound|audio|sfx|camera|graphic)[^\]]*\]", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\[[^\]]*\]", "", s)  # Generic square brackets
    s = re.sub(r"\((?:voiceover|vo|narrator|smiling|pause|whispering|serious|upbeat)[^)]*\)", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^(?:voiceover|narrator|vo|speaker):\s*", "", s, flags=re.IGNORECASE)

    # 2. Strip markdown formatting
    s = re.sub(r"#+\s*", "", s)                       # Markdown headings
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)           # Bold **text**
    s = re.sub(r"\*([^*]+)\*", r"\1", s)               # Italics *text*
    s = re.sub(r"__([^_]+)__", r"\1", s)               # Bold __text__
    s = re.sub(r"_([^_]+)_", r"\1", s)                 # Italics _text_
    s = re.sub(r"~~([^~]+)~~", r"\1", s)               # Strikethrough
    s = re.sub(r"`([^`]+)`", r"\1", s)                 # Code backticks
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)     # Markdown links: [anchor](url) -> anchor
    s = re.sub(r"https?://\S+", "", s)                 # Standalone URLs
    s = re.sub(r"^\s*[-*•]\s+", "", s, flags=re.MULTILINE) # Bullet points
    s = re.sub(r"^\s*\d+\.\s+", "", s, flags=re.MULTILINE) # Numbered lists

    # 3. Currency symbol normalizations for spoken delivery
    # S$500, SGD 500 -> 500 Singapore dollars
    s = re.sub(r"(?:S\$|SGD\s*)(\d+(?:,\d+)*(?:\.\d+)?)", r"\1 Singapore dollars", s, flags=re.IGNORECASE)
    # RM 500, MYR 500 -> 500 Ringgit
    s = re.sub(r"(?:RM\s*|MYR\s*)(\d+(?:,\d+)*(?:\.\d+)?)", r"\1 Ringgit", s, flags=re.IGNORECASE)
    # HK$500, HKD 500 -> 500 Hong Kong dollars
    s = re.sub(r"(?:HK\$|HKD\s*)(\d+(?:,\d+)*(?:\.\d+)?)", r"\1 Hong Kong dollars", s, flags=re.IGNORECASE)
    # US$500, USD 500, $500 -> 500 US dollars
    s = re.sub(r"(?:US\$|USD\s*)(\d+(?:,\d+)*(?:\.\d+)?)", r"\1 U-S dollars", s, flags=re.IGNORECASE)
    s = re.sub(r"\$(\d+(?:,\d+)*(?:\.\d+)?)", r"\1 dollars", s)

    # 4. Acronym & abbreviation expansions
    for pattern, replacement in ACRONYM_PRONUNCIATION_MAP.items():
        s = re.sub(pattern, replacement, s)

    for pattern, replacement in ABBREVIATION_MAP.items():
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

    # Shorthand with slashes
    s = re.sub(r"(^|\s)w/o(?=\s|[.,!?]|$)", r"\1without", s, flags=re.IGNORECASE)
    s = re.sub(r"(^|\s)w/(?=\s|[.,!?]|$)", r"\1with", s, flags=re.IGNORECASE)

    # 5. Symbol normalizations
    s = re.sub(r"\s*&\s*", " and ", s)
    s = re.sub(r"\s*%\s*", " percent ", s)
    s = re.sub(r"\s*\+\s*", " plus ", s)
    s = re.sub(r"(?<=\w)/(?=\w)", " or ", s)  # "and/or" -> "and or"

    # 6. Punctuation cleanup for clean gTTS pacing
    s = re.sub(r"\.{2,}", ".", s)       # Replace multiple dots (ellipses) with single period
    s = re.sub(r"!{2,}", "!", s)       # Replace multiple exclamation marks
    s = re.sub(r"\?{2,}", "?", s)       # Replace multiple question marks
    s = re.sub(r"\s+([,.:;?!])", r"\1", s)  # Remove space before punctuation
    s = re.sub(r"\s+", " ", s)         # Collapse multiple whitespace characters

    return s.strip()


class VoiceAgent:
    """
    Voice Agent orchestration layer.
    Prepares, validates, and normalizes script text generated by Content Agent
    into high-fidelity, speech-ready formats before handing off to speech synthesis.
    """

    def __init__(self):
        self.logger = logger

    def format_for_speech(self, text: str) -> str:
        """Clean an arbitrary voiceover text string for TTS."""
        return clean_voiceover_text(text)

    def prepare_scene(self, scene: VideoScene) -> VideoScene:
        """
        Prepares an individual VideoScene for voiceover synthesis:
        cleans voiceover text, preserving duration and visual descriptors.
        """
        if scene.voiceover:
            cleaned = clean_voiceover_text(scene.voiceover)
            scene.voiceover = cleaned
        return scene

    def prepare_video_script(self, script: VideoScript) -> VideoScript:
        """
        Prepares a complete VideoScript from the Content Agent:
        Iterates over all ordered scenes, sanitizes each voiceover string,
        and prepares it for gTTS synthesis.
        """
        if not script.scenes:
            return script

        for scene in script.scenes:
            self.prepare_scene(scene)

        self.logger.info(
            f"Voice Agent formatted {len(script.scenes)} scenes for brand '{script.brand or 'default'}' into voice-ready text."
        )
        return script

    def process_and_synthesize(
        self,
        script: VideoScript,
        language_override: Optional[str] = None
    ) -> VoiceGenerationResult:
        """
        Full Voice Agent pipeline:
        1. Prepares & normalizes script text from Content Agent.
        2. Dispatches to voice_service for gTTS audio synthesis.
        3. Returns generation result with audio URL ready for video assembly.
        """
        from app.services.voice_service import voice_service

        prepared_script = self.prepare_video_script(script)
        result = voice_service.synthesize_from_script(
            script=prepared_script,
            language_override=language_override
        )
        self.logger.info(
            f"Voice Agent synthesized audio: {result.audio_filename} (duration: {result.duration_seconds}s)"
        )
        return result


# Singleton instance
voice_agent = VoiceAgent()
