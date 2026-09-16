from dataclasses import dataclass

from behave.runner import Context

from src.tests.bdd.helpers.behave_helpers.asserts import BehaveAssertsHelper
from src.tests.bdd.helpers.behave_helpers.parse import BehaveParseHelper
from src.tests.helpers.factory import FactoryHelper


@dataclass(frozen=True, slots=True, kw_only=True)
class BehaveHelper:
    context: Context
    factory: FactoryHelper
    asserts: BehaveAssertsHelper
    parse: BehaveParseHelper
