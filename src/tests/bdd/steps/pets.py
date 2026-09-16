from behave import given, then, when

from src.core.pets.use_cases import CreatePetUseCase
from src.tests.bdd.environment import Context


@given("Существующие питомцы")  # ty: ignore[call-non-callable]
def given_existing_pets(context: Context) -> None:
    for pet in context.bdd.parse.pets():
        context.pet_storage_helper.add_pet(pet=pet)


@when("Создание питомца")  # ty: ignore[call-non-callable]
async def when_creates_pet(context: Context) -> None:
    use_case = CreatePetUseCase(pet_storage=context.pet_storage)
    context.pet_result = await use_case.execute(
        params=context.bdd.parse.create_pet_params(),
    )


@then("Создан питомец")  # ty: ignore[call-non-callable]
def then_pet_is_created(context: Context) -> None:
    context.bdd.asserts.pet(
        actual=context.bdd.asserts.not_none(context.pet_result),
        expected=context.bdd.parse.pet(),
    )


@then("Существующие питомцы")  # ty: ignore[call-non-callable]
def then_existing_pets(context: Context) -> None:
    context.bdd.asserts.pets(
        actual=context.pet_storage_helper.get_pets(),
        expected=context.bdd.parse.pets(),
    )


@then("Питомец передан в хранилище")  # ty: ignore[call-non-callable]
def then_pet_is_passed_to_storage(context: Context) -> None:
    context.pet_storage.create_pet.assert_awaited_once_with(
        pet=context.bdd.parse.pet(),
    )
