# Reference: server-generated value

## Статус в проекте

[GeneralProvider](../../src/di/providers/general.py) уже предоставляет UUID и UTC datetime. `/health` их не запрашивает; registration и бизнес-endpoints отсутствуют.

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: Entity with a server-generated value

```python
class CreateEntityRequest(BoundaryModel):
    name: str
    amount: Decimal

    def to_domain(self, *, entity_id: UUID) -> EntityWithGeneratedIdParams:
        return EntityWithGeneratedIdParams(
            id=entity_id.int,
            name=self.name,
            description="",
            status=EntityStatusEnum.ACTIVE,
            amount=self.amount,
        )


@router.post(path="", status_code=status.HTTP_201_CREATED)
async def create_entity_with_generated_id(
    body: CreateEntityRequest,
    entity_id: FromDishka[UUID],
    use_case: FromDishka[CreateEntityWithGeneratedIdUseCase],
) -> EntityResponse:
    result = await use_case.execute(
        params=body.to_domain(entity_id=entity_id),
    )
    return EntityResponse.from_domain(entity=result.entity)
```

Паттерн подходит, если domain contract требует identity на delivery boundary. Params, use case,
response и test provider нужно определить вместе. Он не подменяет database-generated identity;
детерминированный test provider в текущем проекте ещё отсутствует.
