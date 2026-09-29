import logging
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from fastapi import HTTPException, status
from pydantic import Field, HttpUrl, ValidationError, model_validator

from src.infra.api.boundary import BoundaryModel

logger = logging.getLogger(__name__)
MATERIALS_PATH = Path(__file__).parent / "data" / "materials.json"
EXPECTED_SKILL_IDS = frozenset(f"FIN-{number:02d}" for number in range(1, 13))


class PublicationStatus(StrEnum):
    UNPUBLISHED = "UNPUBLISHED"
    PUBLISHED = "PUBLISHED"


class SkillContent(BoundaryModel):
    skill_id: Annotated[str, Field(pattern=r"^FIN-(0[1-9]|1[0-2])$")]
    learning_goal: Annotated[str, Field(min_length=1)]
    story: Annotated[str, Field(min_length=1)]
    replace_with_parent_story: Annotated[str, Field(min_length=1)]
    conversation_starters: Annotated[list[str], Field(min_length=5, max_length=5)]
    parent_takeaway: Annotated[str, Field(min_length=1)]
    research_basis: Annotated[str, Field(min_length=1)]
    research_sources: Annotated[list[str], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_content(self) -> Self:  # noqa: N804 - Pydantic after-validator uses the instance
        text = [
            self.learning_goal,
            self.story,
            self.replace_with_parent_story,
            self.parent_takeaway,
            self.research_basis,
            *self.conversation_starters,
        ]
        if any(not value.strip() for value in text):
            message = "Parent materials cannot contain blank text"
            raise ValueError(message)
        if any(
            not url.startswith("https://")
            or not urlsplit(url).hostname
            or HttpUrl(url).scheme != "https"
            for url in self.research_sources
        ):
            message = "Research sources must be HTTPS links"
            raise ValueError(message)
        return self


class ParentMaterialsResponse(BoundaryModel):
    schema_version: Literal[1] = 1
    content_version: Annotated[str, Field(min_length=1)]
    publication_status: PublicationStatus = PublicationStatus.PUBLISHED
    skills: list[SkillContent]

    @model_validator(mode="after")
    def validate_publication(self) -> Self:  # noqa: N804 - Pydantic after-validator uses the instance
        if not self.content_version.strip():
            message = "The catalogue content version cannot be blank"
            raise ValueError(message)
        if self.publication_status == PublicationStatus.UNPUBLISHED:
            if self.skills:
                message = "An unpublished catalogue must have no skills"
                raise ValueError(message)
        elif (
            len(self.skills) != len(EXPECTED_SKILL_IDS)
            or {skill.skill_id for skill in self.skills} != EXPECTED_SKILL_IDS
        ):
            message = "A published catalogue must contain each FIN skill exactly once"
            raise ValueError(message)
        return self


def load_parent_materials() -> ParentMaterialsResponse:
    try:
        content = MATERIALS_PATH.read_text(encoding="utf-8")
        return ParentMaterialsResponse.parse_json(content)
    except FileNotFoundError:
        return ParentMaterialsResponse(
            content_version="unpublished",
            publication_status=PublicationStatus.UNPUBLISHED,
            skills=[],
        )
    except (OSError, UnicodeError, ValidationError) as error:
        logger.exception("Parent materials catalogue could not be loaded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PARENT_MATERIALS_UNAVAILABLE",
        ) from error
