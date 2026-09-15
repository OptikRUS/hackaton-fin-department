# Reference: BDD automation

## Статус в проекте

Behave не установлен; `src/tests/bdd`, Context, Feature/steps и BDD helpers отсутствуют. `make tests` запускает только pytest.

Ниже сохранён переносимый паттерн из исходного набора references. Это пример для будущего
расширения, а не существующие классы, пути или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: data shapes

Коллекция задаётся горизонтальной таблицей: один объект на строку. Для одного объекта с
разнородными полями можно использовать vertical field/value table. До и после события форма
коллекции остаётся сопоставимой; пустая коллекция задаётся headings без data rows.

```gherkin
Given Существующие сущности
| id | name            | status |
| 1  | Первая сущность | active |
When Пользователь создаёт сущность
| field  | value           |
| name   | Вторая сущность |
| status | draft           |
Then Существующие сущности
| id | name            | status |
| 1  | Первая сущность | active |
| 2  | Вторая сущность | draft  |
```

Entity и table fields заменяются согласованными domain terms. HTTP, SQL, DI и Python class names
не добавляются в бизнес-сценарий.

## REUSABLE PATTERN: context и helpers

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class BehaveHelper:
    context: Context
    factory: FactoryHelper
    asserts: BehaveAssertsHelper
    parse: BehaveParseHelper
    core: BehaveCoreHelper
```

На каждый Scenario создаются свежие typed Context, factories, stateful fakes, strict
`AsyncMock(spec=Port, wraps=fake)`, deterministic services и пустые result/error slots.
Parse helper проверяет точные headings и число строк, преобразует literal values через factory.
Core helper связывает человекочитаемые значения и ошибки с domain types; asserts helper
сравнивает целые domain objects. Helpers не содержат бизнес-оркестрацию.

Given и Then состояния работают с fake; use case получает mock с wraps. Это позволяет
проверять и состояние, и exact named interaction без ложных вызовов во время setup.
Обязательная попытка вызова port проверяется `assert_awaited_once_with`, запрещённая —
`assert_not_awaited()`. Неизменившееся состояние само по себе не доказывает отсутствие вызова.

## Подключение и validation

Перед добавлением BDD определить capabilities, зависимости, typed context, parser и команды.
Semantic review сценариев и Behave syntax/bindings — разные проверки. Исходный проект использовал
отдельный `$bdd-quality`; этот skill и его правила не поставляются этим каталогом.
Documentation-only перенос не добавляет executable scenarios и не требует Behave-запуска.
