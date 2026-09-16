from alembic.command import downgrade as alembic_downgrade
from alembic.command import upgrade as alembic_upgrade
from alembic.config import Config

from src.config.constants import constants


def migrate(revision: str, db_url: str) -> None:
    config = Config(constants.DIRS.SRC / "infra" / "migrations" / "alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    alembic_upgrade(config=config, revision=revision)


def downgrade(revision: str, db_url: str) -> None:
    config = Config(constants.DIRS.SRC / "infra" / "migrations" / "alembic.ini")
    config.set_main_option("sqlalchemy.url", db_url)
    alembic_downgrade(config=config, revision=revision)
