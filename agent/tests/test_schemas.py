"""Tests for agent.schemas (Task A4)."""

import pytest
from pydantic import ValidationError

from schemas import DossierCreate, ProjectCreate, Source


def test_project_title_over_120_chars_raises_validation_error():
    with pytest.raises(ValidationError):
        ProjectCreate(title='x' * 121)


def test_dossier_question_over_500_chars_raises_validation_error():
    with pytest.raises(ValidationError):
        DossierCreate(question='q' * 501)


def test_valid_project_create_roundtrip_keeps_defaults():
    project = ProjectCreate(title='Verisim')

    data = project.model_dump()
    assert data['logline'] == ''
    assert data['genre'] == ''

    restored = ProjectCreate(**data)
    assert restored == project
    assert restored.logline == ''
    assert restored.genre == ''


def test_valid_source_with_url_parses_n():
    source = Source(
        n=1,
        title='Example',
        url='https://example.com/x',
        excerpt='An excerpt.',
    )

    assert source.n == 1
    assert str(source.url) == 'https://example.com/x'
