import json
from asyncio import to_thread
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from src.infra.api.parents import skill_content
from src.infra.api.parents.skill_content import ParentMaterialsResponse
from src.tests.fixtures import APIFixture

UNPUBLISHED = {
    "schemaVersion": 1,
    "contentVersion": "unpublished",
    "publicationStatus": "UNPUBLISHED",
    "skills": [],
}


@pytest.fixture
def catalogue_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "materials.json"
    monkeypatch.setattr(skill_content, "MATERIALS_PATH", path)
    return path


@pytest.fixture
def published_catalogue() -> dict[str, Any]:
    # Synthetic data is only for exercising publication validation and API mapping.
    return {
        "schemaVersion": 1,
        "contentVersion": "test-published-v1",
        "publicationStatus": "PUBLISHED",
        "skills": [
            {
                "skillId": f"FIN-{number:02d}",
                "learningGoal": f"Test learning goal {number}",
                "story": f"Test story {number}",
                "replaceWithParentStory": f"Test parent story prompt {number}",
                "conversationStarters": [
                    f"Test question {number}.{question}?" for question in range(5)
                ],
                "parentTakeaway": f"Test takeaway {number}",
                "researchBasis": f"Test research basis {number}",
                "researchSources": [f"https://example.com/test-research/{number}"],
            }
            for number in range(1, 13)
        ],
    }


class TestParentMaterialsAPI(APIFixture):
    async def test_catalogue_is_unpublished_without_profile_or_skill_assessment(self) -> None:
        response = await self.api.client.get("/v1/parent-materials")
        assert response.status_code == 200
        assert response.json() == UNPUBLISHED

    async def test_missing_optional_catalogue_is_unpublished(self, catalogue_path: Path) -> None:
        assert not await to_thread(catalogue_path.exists)
        response = await self.api.client.get("/v1/parent-materials")
        assert response.status_code == 200
        assert response.json() == UNPUBLISHED
        report = await self.api.get_parent_report(pet_id="test-device")
        assert report.status_code == 200
        assert len(report.json()["skills"]) == 12
        assert all(not skill["materialsAvailable"] for skill in report.json()["skills"])

    @pytest.mark.parametrize(
        "content",
        [
            b"{invalid",
            b"\xff",
            b"{}",
            json.dumps({**UNPUBLISHED, "publicationStatus": "PUBLISHED"}).encode(),
        ],
    )
    async def test_invalid_catalogue_is_controlled_and_health_remains_available(
        self,
        catalogue_path: Path,
        content: bytes,
    ) -> None:
        await to_thread(catalogue_path.write_bytes, content)
        response = await self.api.client.get("/v1/parent-materials")
        assert response.status_code == 503
        assert response.json() == {"detail": "PARENT_MATERIALS_UNAVAILABLE"}
        report = await self.api.get_parent_report(pet_id="test-device")
        assert report.status_code == 503
        health = await self.api.client.get("/health")
        assert health.status_code == 200
        assert health.content == b""
        # Replacing a bad file must allow the next request to succeed without a restart.
        await to_thread(catalogue_path.write_text, json.dumps(UNPUBLISHED), encoding="utf-8")
        recovered = await self.api.client.get("/v1/parent-materials")
        assert recovered.status_code == 200
        assert recovered.json() == UNPUBLISHED

    async def test_published_legacy_report_and_catalogue_share_the_same_materials(
        self,
        catalogue_path: Path,
        published_catalogue: dict[str, Any],
    ) -> None:
        await to_thread(
            catalogue_path.write_text, json.dumps(published_catalogue), encoding="utf-8"
        )
        catalogue = await self.api.client.get("/v1/parent-materials")
        assert catalogue.status_code == 200
        assert catalogue.json() == published_catalogue
        report = await self.api.get_parent_report(pet_id="test-device")
        assert report.status_code == 200
        legacy = {skill["id"]: skill for skill in report.json()["skills"]}
        for material in published_catalogue["skills"]:
            assert legacy[material["skillId"]]["materialsAvailable"] is True
            for field, value in material.items():
                if field != "skillId":
                    assert legacy[material["skillId"]][field] == value
            assert "status" not in material
            assert "isMastered" not in material
        assert "pet" not in catalogue.json()


class TestParentMaterialsValidation:
    def test_unpublished_catalogue_must_be_empty(self, published_catalogue: dict[str, Any]) -> None:
        published_catalogue["publicationStatus"] = "UNPUBLISHED"
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)

    @pytest.mark.parametrize("count", [0, 11, 13])
    def test_published_catalogue_requires_twelve_skills(
        self,
        published_catalogue: dict[str, Any],
        count: int,
    ) -> None:
        published_catalogue["skills"] = (published_catalogue["skills"] * 2)[:count]
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)

    def test_published_catalogue_requires_unique_ids(
        self, published_catalogue: dict[str, Any]
    ) -> None:
        published_catalogue["skills"][0]["skillId"] = "FIN-02"
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)

    @pytest.mark.parametrize("skill_id", ["FIN-00", "FIN-13", "FIN-1"])
    def test_published_catalogue_rejects_unknown_ids(
        self,
        published_catalogue: dict[str, Any],
        skill_id: str,
    ) -> None:
        published_catalogue["skills"][0]["skillId"] = skill_id
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)

    @pytest.mark.parametrize("questions", [[], ["Question?"] * 4, ["Question?"] * 6, [" "] * 5])
    def test_published_catalogue_requires_five_nonblank_questions(
        self,
        published_catalogue: dict[str, Any],
        questions: list[str],
    ) -> None:
        published_catalogue["skills"][0]["conversationStarters"] = questions
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)

    @pytest.mark.parametrize(
        "field",
        ["learningGoal", "story", "replaceWithParentStory", "parentTakeaway", "researchBasis"],
    )
    def test_published_catalogue_requires_nonblank_metadata(
        self,
        published_catalogue: dict[str, Any],
        field: str,
    ) -> None:
        published_catalogue["skills"][0][field] = " \n"
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)

    @pytest.mark.parametrize(
        "sources",
        [
            [],
            [""],
            ["http://example.com"],
            ["https://"],
            ["https://bad host"],
            ["https:example.com"],
            ["https:///example.com"],
            [" https://example.com"],
        ],
    )
    def test_published_catalogue_requires_https_sources(
        self,
        published_catalogue: dict[str, Any],
        sources: list[str],
    ) -> None:
        published_catalogue["skills"][0]["researchSources"] = sources
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)

    def test_catalogue_requires_nonblank_content_version(
        self, published_catalogue: dict[str, Any]
    ) -> None:
        published_catalogue["contentVersion"] = " "
        with pytest.raises(ValidationError):
            ParentMaterialsResponse.parse(published_catalogue)
