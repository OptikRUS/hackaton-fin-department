# Repository Coverage



| Name                                                |    Stmts |     Miss |   Cover |   Missing |
|---------------------------------------------------- | -------: | -------: | ------: | --------: |
| src/\_\_init\_\_.py                                 |        0 |        0 |    100% |           |
| src/config/\_\_init\_\_.py                          |        0 |        0 |    100% |           |
| src/config/constants.py                             |        9 |        0 |    100% |           |
| src/config/settings.py                              |       35 |        0 |    100% |           |
| src/core/\_\_init\_\_.py                            |        0 |        0 |    100% |           |
| src/core/pets/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| src/core/pets/schemas.py                            |        7 |        0 |    100% |           |
| src/core/pets/storages.py                           |        5 |        0 |    100% |           |
| src/core/pets/use\_cases.py                         |       10 |        0 |    100% |           |
| src/core/use\_case.py                               |        5 |        0 |    100% |           |
| src/di/\_\_init\_\_.py                              |        0 |        0 |    100% |           |
| src/di/container.py                                 |        7 |        0 |    100% |           |
| src/di/providers/\_\_init\_\_.py                    |        0 |        0 |    100% |           |
| src/di/providers/general.py                         |       10 |        2 |     80% |    10, 14 |
| src/di/providers/pets.py                            |        7 |        1 |     86% |        10 |
| src/di/providers/postgres.py                        |       19 |        8 |     58% | 14-20, 24 |
| src/infra/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| src/infra/api/\_\_init\_\_.py                       |        0 |        0 |    100% |           |
| src/infra/api/app.py                                |       29 |        0 |    100% |           |
| src/infra/api/boundary.py                           |       17 |        3 |     82% |19, 23, 26 |
| src/infra/api/common/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| src/infra/api/common/endpoints.py                   |        5 |        0 |    100% |           |
| src/infra/api/exceptions.py                         |        9 |        1 |     89% |        12 |
| src/infra/api/pets/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| src/infra/api/pets/endpoints.py                     |       10 |        0 |    100% |           |
| src/infra/api/pets/schemas.py                       |       11 |        0 |    100% |           |
| src/infra/api/routers.py                            |        6 |        0 |    100% |           |
| src/infra/migrations/\_\_init\_\_.py                |        0 |        0 |    100% |           |
| src/infra/migrations/commands.py                    |       12 |        0 |    100% |           |
| src/infra/migrations/env.py                         |       40 |        9 |     78% |25-29, 36-43, 74 |
| src/infra/migrations/versions/0001\_create\_pets.py |       11 |        0 |    100% |           |
| src/infra/migrations/versions/\_\_init\_\_.py       |        0 |        0 |    100% |           |
| src/infra/observability/\_\_init\_\_.py             |        0 |        0 |    100% |           |
| src/infra/observability/metrics.py                  |       14 |        0 |    100% |           |
| src/infra/observability/tracing.py                  |       12 |        0 |    100% |           |
| src/infra/storages/\_\_init\_\_.py                  |        0 |        0 |    100% |           |
| src/infra/storages/postgres/\_\_init\_\_.py         |        0 |        0 |    100% |           |
| src/infra/storages/postgres/config.py               |        4 |        0 |    100% |           |
| src/infra/storages/postgres/models.py               |       19 |        0 |    100% |           |
| src/infra/storages/postgres/pet\_storage.py         |       12 |        0 |    100% |           |
| **TOTAL**                                           |  **325** |   **24** | **93%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://github.com/OptikRUS/hackaton-fin-department/raw/python-coverage-comment-action-data/badge.svg)](https://github.com/OptikRUS/hackaton-fin-department/tree/python-coverage-comment-action-data)

This is the one to use if your repository is private or if you don't want to customize anything.



## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.