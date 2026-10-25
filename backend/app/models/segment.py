from typing import List, Optional
from pydantic import BaseModel, Field


class WordTimestamp(BaseModel):
    """Precise word-level acoustic alignment timestamp."""
    word: str = Field(..., description="Individual word token")
    start_ms: int = Field(..., description="Start offset in milliseconds")
    end_ms: int = Field(..., description="End offset in milliseconds")
    start_time: float = Field(..., description="Start offset in seconds")
    end_time: float = Field(..., description="End offset in seconds")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="ASR alignment confidence score")


class IsochronicSegment(BaseModel):
    """
    Time-coded phrasing segment with duration budgeting and syllable pacing
    engineered specifically for neural lip-sync synchronization.
    """
    segment_id: int = Field(..., description="1-indexed sequence identifier")
    start_time: float = Field(..., description="Segment start offset in seconds")
    end_time: float = Field(..., description="Segment end offset in seconds")
    start_ms: int = Field(..., description="Segment start offset in milliseconds")
    end_ms: int = Field(..., description="Segment end offset in milliseconds")
    duration_budget: float = Field(..., description="Exact duration allowed for the spoken sentence (seconds)")
    source_text: str = Field(..., description="Original transcribed speech in source language")
    target_text: str = Field(..., description="Isochronic translation in target native script (e.g. Telugu, Hindi, Tamil, Spanish)")
    phonetic_text: str = Field(..., description="Phonetic Romanized script (e.g. Teluglish, Hinglish, Romanized)")
    original_syllables: int = Field(..., description="Count of syllables in the original audio segment")
    target_syllables: int = Field(..., description="Count of syllables in the translated sentence")
    pacing_ratio: float = Field(..., description="Target-to-source syllable ratio (ideal is ~1.0 within ±10%)")
    fit_status: str = Field(..., description="'FITS', 'TOO_LONG', or 'TOO_SHORT' relative to time budget")
    tolerance_pct: float = Field(..., description="Percentage deviation from original syllable count")
    speaker_id: Optional[str] = Field(default="SPEAKER_00", description="Diarized speaker label")
    words: List[WordTimestamp] = Field(default_factory=list, description="Word-level acoustic breakdown")
    is_curated: bool = Field(default=False, description="True if manually edited or verified by human curator")


class SegmentUpdateRequest(BaseModel):
    """Human-in-the-loop curation payload for editing translated words and phrasing."""
    segment_id: int = Field(..., description="ID of segment to edit")
    target_text: Optional[str] = Field(default=None, description="Updated native script text")
    phonetic_text: Optional[str] = Field(default=None, description="Updated phonetic Romanized text")
    words: Optional[List[WordTimestamp]] = Field(default=None, description="Updated word breakdowns if timing adjusted")


class SegmentsBatchUpdateRequest(BaseModel):
    """Payload to batch update multiple segments."""
    segments: List[SegmentUpdateRequest] = Field(..., description="List of segment modifications")


class SegmentsListResponse(BaseModel):
    """Full time-coded segment list returned by GET /api/v1/projects/{job_id}/segments."""
    job_id: str
    target_language: str
    total_segments: int
    all_fit: bool
    segments: List[IsochronicSegment]


class SegmentsBatchUpdateResponse(BaseModel):
    """Response returned by PUT /api/v1/projects/{job_id}/segments."""
    job_id: str
    updated_count: int
    all_fit: bool
    segments: List[IsochronicSegment]
    message: str
