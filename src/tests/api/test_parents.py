import pytest
from httpx2 import codes

from src.tests.fixtures import APIFixture


class TestGetParentReportAPI(APIFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.pet_id = "12345678123456781234567812345678"

    async def test_returns_pet_and_twelve_demo_skills(self) -> None:
        response = await self.api.get_parent_report(pet_id=self.pet_id)

        assert response.status_code == codes.OK
        assert response.json() == {
            "pet": {
                "id": self.pet_id,
                "name": "Рыжик",
                "temper": "playful",
                "balance": 100,
                "selectedLookId": "BACKPACK",
                "visualState": "NORMAL",
            },
            "skills": [
                {
                    "id": "FIN-01",
                    "title": "Сравнивает денежные суммы",
                    "status": "MASTERED",
                    "isMastered": True,
                },
                {
                    "id": "FIN-02",
                    "title": "Планирует бюджет на период",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
                {
                    "id": "FIN-03",
                    "title": "Учитывает обязательные нужды перед желаниями",
                    "status": "PRACTICING",
                    "isMastered": False,
                },
                {
                    "id": "FIN-04",
                    "title": "Следит, чтобы денег хватало до следующего дохода",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
                {
                    "id": "FIN-05",
                    "title": "Последовательно собирает на выбранную цель",
                    "status": "MASTERED",
                    "isMastered": True,
                },
                {
                    "id": "FIN-06",
                    "title": "Откладывает желанную покупку ради приоритета",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
                {
                    "id": "FIN-07",
                    "title": "Создаёт запас на непредвиденные расходы",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
                {
                    "id": "FIN-08",
                    "title": "Перестраивает действия после неожиданной траты",
                    "status": "PRACTICING",
                    "isMastered": False,
                },
                {
                    "id": "FIN-09",
                    "title": "Сопоставляет денежные и другие затраты",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
                {
                    "id": "FIN-10",
                    "title": "Планирует дополнительный заработок",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
                {
                    "id": "FIN-11",
                    "title": "Разбирает финансовые последствия и меняет решение",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
                {
                    "id": "FIN-12",
                    "title": "Понимает свои доходы и расходы",
                    "status": "NO_DATA",
                    "isMastered": None,
                },
            ],
            "isDemo": True,
        }

    async def test_returns_demo_for_another_valid_pet_id(self) -> None:
        response = await self.api.get_parent_report(
            pet_id="87654321876543218765432187654321",
        )

        assert response.status_code == codes.OK
        assert response.json()["pet"]["id"] == "87654321876543218765432187654321"
        assert response.json()["isDemo"] is True

    async def test_accepts_saved_device_id(self) -> None:
        response = await self.api.get_parent_report(pet_id="9f1c2d3e4a5b6078")

        assert response.status_code == codes.OK
        assert response.json()["pet"]["id"] == "9f1c2d3e4a5b6078"
