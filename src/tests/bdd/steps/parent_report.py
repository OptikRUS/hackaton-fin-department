import json
from dataclasses import replace

from behave import given, then, when

from src.core.parents.exceptions import ParentReportNotFoundError
from src.core.parents.use_cases import GetParentReportUseCase
from src.core.profiles.schemas import DeviceId
from src.tests.bdd.environment import Context


@given(  # ty: ignore[call-non-callable]
    'Профиль отчёта "{device_id}" с именем "{name}", темпераментом "{temper}" и образом "{look}"'
)
def given_parent_profile(
    context: Context, device_id: str, name: str, temper: str, look: str
) -> None:
    context.parent_device_id = device_id
    profile_id = DeviceId(value=device_id).profile_id
    profile = context.factory.profiles.registered_profile(
        profile_id=profile_id, device_id=device_id, pet_name=name
    )
    context.parent_profile_storage.get_profile.return_value = replace(
        profile,
        pet=replace(profile.pet, temperament=temper, selected_look_id=look),
    )


@given('Архив отчёта для "{device_id}" и прохождения "{run_id}" содержит')  # ty: ignore[call-non-callable]
def given_parent_snapshot(
    context: Context,
    device_id: str,
    run_id: str,
) -> None:
    row = context.table[0]
    snapshot_json = json.dumps({
        "formatVersion": 5,
        "runId": run_id,
        "state": {
            "pet": {
                "name": row["name"],
                "temperament": row["temper"],
                "selectedLookId": row["look"],
                "visualState": row["visual"],
            },
            "economy": {
                "availableBalance": int(row["available"]),
                "savingsBalance": int(row["savings"]),
            },
        },
    })
    context.parent_snapshot_storage.get_latest.return_value = context.factory.snapshots.snapshot(
        profile_id=DeviceId(value=device_id).profile_id,
        game_run_id=run_id,
        snapshot_json=snapshot_json,
    )


@given(  # ty: ignore[call-non-callable]
    'Оценка отчёта для "{run_id}" содержит FIN-01 "{first}",'
    ' FIN-11 "{eleventh}", остальные "{other}"'
)
def given_parent_assessment(
    context: Context, run_id: str, first: str, eleventh: str, other: str
) -> None:
    baseline = context.factory.analytics.assessment(status=other)
    assert context.parent_device_id is not None
    expected_profile_id = DeviceId(value=context.parent_device_id).profile_id
    context.parent_analytics_storage.get_assessment.side_effect = (
        lambda *, profile_id, game_run_id: (
            replace(
                baseline,
                game_run_id=run_id,
                skills=tuple(
                    replace(
                        skill,
                        status=(
                            first
                            if skill.skill_id == "FIN-01"
                            else eleventh
                            if skill.skill_id == "FIN-11"
                            else other
                        ),
                    )
                    for skill in baseline.skills
                ),
            )
            if profile_id == expected_profile_id and game_run_id == run_id
            else None
        )
    )


@when('Родитель запрашивает отчёт для "{device_id}"')  # ty: ignore[call-non-callable]
async def when_parent_requests_report(context: Context, device_id: str) -> None:
    use_case = GetParentReportUseCase(
        profile_storage=context.parent_profile_storage,
        snapshot_storage=context.parent_snapshot_storage,
        analytics_storage=context.parent_analytics_storage,
    )
    try:
        context.parent_report = await use_case.execute(device_id=device_id)
    except ParentReportNotFoundError as error:
        context.parent_error = error


@then(  # ty: ignore[call-non-callable]
    'Питомец отчёта "{name}" с темпераментом "{temper}", образом "{look}",'
    ' балансом "{balance}" и состоянием "{visual}"'
)
def then_parent_pet(
    context: Context, name: str, temper: str, look: str, balance: str, visual: str
) -> None:
    report = context.parent_report
    assert report is not None
    assert report.pet.name == name
    assert report.pet.temper == temper
    assert report.pet.selected_look_id == look
    assert report.pet.balance == (None if balance == "null" else int(balance))
    assert report.pet.visual_state == (None if visual == "null" else visual)


@then('Все 12 навыков отчёта имеют статус "{status}"')  # ty: ignore[call-non-callable]
def then_all_parent_skills(context: Context, status: str) -> None:
    report = context.parent_report
    assert report is not None
    assert len(report.skill_statuses) == 12
    assert {skill.status for skill in report.skill_statuses} == {status}


@then(  # ty: ignore[call-non-callable]
    'Навыки отчёта содержат FIN-01 "{first}", FIN-11 "{eleventh}", остальные "{other}"'
)
def then_parent_skills(context: Context, first: str, eleventh: str, other: str) -> None:
    report = context.parent_report
    assert report is not None
    assert {skill.skill_id: skill.status for skill in report.skill_statuses} == {
        f"FIN-{number:02d}": (first if number == 1 else eleventh if number == 11 else other)
        for number in range(1, 13)
    }


@then('Архив отчёта запрошен для "{device_id}", оценка не запрошена')  # ty: ignore[call-non-callable]
def then_snapshot_without_assessment(context: Context, device_id: str) -> None:
    profile_id = DeviceId(value=device_id).profile_id
    context.parent_snapshot_storage.get_latest.assert_awaited_once_with(profile_id=profile_id)
    context.parent_analytics_storage.get_assessment.assert_not_awaited()


@then('Оценка отчёта запрошена для прохождения "{run_id}"')  # ty: ignore[call-non-callable]
def then_assessment_for_run(context: Context, run_id: str) -> None:
    assert context.parent_device_id is not None
    context.parent_analytics_storage.get_assessment.assert_awaited_once_with(
        profile_id=DeviceId(value=context.parent_device_id).profile_id,
        game_run_id=run_id,
    )


@then("Отчёт родителя не найден")  # ty: ignore[call-non-callable]
def then_report_missing(context: Context) -> None:
    assert isinstance(context.parent_error, ParentReportNotFoundError)


@then("Архив и оценка отчёта не запрошены")  # ty: ignore[call-non-callable]
def then_no_report_dependencies(context: Context) -> None:
    context.parent_snapshot_storage.get_latest.assert_not_awaited()
    context.parent_analytics_storage.get_assessment.assert_not_awaited()
