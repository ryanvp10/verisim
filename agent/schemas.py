"""Pydantic v2 schemas for the verisim agent."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ProjectCreate(BaseModel):
    """Payload for creating a new project."""

    title: str = Field(..., max_length=120)
    logline: str = Field('', max_length=500)
    genre: str = Field('', max_length=40)


class ProjectOut(BaseModel):
    """Project representation returned by the API."""

    id: str
    title: str
    logline: str = ''
    genre: str = ''
    dossier_count: int = 0
    created_at: datetime


class Source(BaseModel):
    """A single cited source attached to a dossier answer."""

    n: int = Field(..., ge=1)
    title: str
    url: HttpUrl
    excerpt: str = Field(..., max_length=500)


class DossierCreate(BaseModel):
    """Payload for creating a dossier (asking a question)."""

    question: str = Field(..., max_length=500)


class DossierOut(BaseModel):
    """Dossier representation returned by the API."""

    dossier_id: str
    question: str
    answer: str
    findings: list[str] = []
    notes: list[str] = []
    sources: list[Source] = []
    status: str = 'done'
    created_at: datetime


class ThreadMsgIn(BaseModel):
    """Payload for posting a message to a project thread."""

    message: str = Field(..., max_length=500)


class ThreadMsgOut(BaseModel):
    """Thread message representation returned by the API."""

    role: str
    text: str
    sources_used: list[int] = []
    created_at: datetime
