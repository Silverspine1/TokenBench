"""Pydantic schema for external GitHub source repos."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExternalRepoSource(BaseModel):
    """Metadata for a pinned external GitHub repository."""

    model_config = {"extra": "allow"}

    repo_id: str = Field(min_length=1)
    source_type: str = "github"
    url: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    name: str = Field(min_length=1)
    pinned_commit: str = Field(min_length=7)
    license: str = ""
    language_profile: list[str] = Field(default_factory=list)
    meaningful_file_count: int | None = None
    dependency_policy: str = "offline_after_install"
    setup_commands: list[str] = Field(default_factory=list)
    smoke_commands: list[str] = Field(default_factory=list)
    junk_paths: list[str] = Field(default_factory=list)
    test_runner: str = "pytest"
    test_runner_args: list[str] = Field(default_factory=list)
    file_count_note: str = ""
