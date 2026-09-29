import json
from asyncio import to_thread
from pathlib import Path

import pytest
from httpx2 import codes

from src.core.parents.exceptions import ParentReportNotFoundError
from src.core.parents.schemas import ParentPet, ParentReport, ParentSkillStatus
from src.core.parents.use_cases import GetParentReportUseCase
from src.tests.fixtures import APIFixture, ContainerFixture


class TestGetParentReportAPI(APIFixture, ContainerFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.pet_id = "12345678123456781234567812345678"
        self.skill_materials = json.loads(
            await to_thread(
                (Path(__file__).parent / "data" / "parent_skill_materials.json").read_text,
                encoding="utf-8",
            ),
        )
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=GetParentReportUseCase,
        )
        self.use_case.execute.return_value = ParentReport(
            pet=ParentPet(
                id=self.pet_id,
                name="Лис",
                temper=None,
                balance=None,
                selected_look_id="PLAIN",
                visual_state=None,
            ),
            skill_statuses=tuple(
                ParentSkillStatus(
                    skill_id=f"FIN-{number:02d}",
                    status=(
                        "MASTERED" if number == 1 else "HAS_PROBLEM" if number == 11 else "NO_DATA"
                    ),
                )
                for number in range(1, 13)
            ),
        )

    async def test_returns_real_pet_and_twelve_saved_skills(self) -> None:
        response = await self.api.get_parent_report(pet_id=self.pet_id)

        assert response.status_code == codes.OK
        assert response.json() == {
            "pet": {
                "id": self.pet_id,
                "name": "Лис",
                "temper": None,
                "balance": None,
                "selectedLookId": "PLAIN",
                "visualState": None,
            },
            "skills": [
                {
                    "id": "FIN-01",
                    "title": "Сравнивает денежные суммы",
                    "status": "MASTERED",
                    "isMastered": True,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-01"],
                },
                {
                    "id": "FIN-02",
                    "title": "Планирует бюджет на период",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-02"],
                },
                {
                    "id": "FIN-03",
                    "title": "Учитывает обязательные нужды перед желаниями",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-03"],
                },
                {
                    "id": "FIN-04",
                    "title": "Следит, чтобы денег хватало до следующего дохода",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-04"],
                },
                {
                    "id": "FIN-05",
                    "title": "Последовательно собирает на выбранную цель",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-05"],
                },
                {
                    "id": "FIN-06",
                    "title": "Откладывает желанную покупку ради приоритета",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-06"],
                },
                {
                    "id": "FIN-07",
                    "title": "Создаёт запас на непредвиденные расходы",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-07"],
                },
                {
                    "id": "FIN-08",
                    "title": "Перестраивает действия после неожиданной траты",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-08"],
                },
                {
                    "id": "FIN-09",
                    "title": "Сопоставляет денежные и другие затраты",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-09"],
                },
                {
                    "id": "FIN-10",
                    "title": "Планирует дополнительный заработок",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-10"],
                },
                {
                    "id": "FIN-11",
                    "title": "Разбирает финансовые последствия и меняет решение",
                    "status": "HAS_PROBLEM",
                    "isMastered": False,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-11"],
                },
                {
                    "id": "FIN-12",
                    "title": "Понимает свои доходы и расходы",
                    "status": "NO_DATA",
                    "isMastered": None,
                    "materialsAvailable": True,
                    **self.skill_materials["FIN-12"],
                },
            ],
            "isDemo": False,
        }
        self.use_case.execute.assert_awaited_once_with(device_id=self.pet_id)

    async def test_unknown_device_id_returns_not_found(self) -> None:
        self.use_case.execute.side_effect = ParentReportNotFoundError
        response = await self.api.get_parent_report(
            pet_id="87654321876543218765432187654321",
        )

        assert response.status_code == codes.NOT_FOUND
        assert response.json() == {"code": "PARENT_REPORT_NOT_FOUND"}
        self.use_case.execute.assert_awaited_once_with(device_id="87654321876543218765432187654321")

    async def test_accepts_saved_device_id(self) -> None:
        response = await self.api.get_parent_report(pet_id="9f1c2d3e4a5b6078")

        assert response.status_code == codes.OK
        self.use_case.execute.assert_awaited_once_with(device_id="9f1c2d3e4a5b6078")

    async def test_openapi_requires_camel_case_material_fields(self) -> None:
        response = await self.api.client.get(url="/openapi.json")

        assert response.status_code == codes.OK
        schema = response.json()["components"]["schemas"]["SkillResponse"]
        material_types = {
            "learningGoal": "string",
            "story": "string",
            "replaceWithParentStory": "string",
            "conversationStarters": "array",
            "parentTakeaway": "string",
            "researchBasis": "string",
            "researchSources": "array",
        }
        expected_fields = {
            "id",
            "title",
            "status",
            "isMastered",
            "materialsAvailable",
            *material_types,
        }
        assert set(schema["properties"]) == expected_fields
        assert set(schema["required"]) == expected_fields
        for field, field_type in material_types.items():
            assert schema["properties"][field]["type"] == field_type
            if field_type == "array":
                assert schema["properties"][field]["items"] == {"type": "string"}
