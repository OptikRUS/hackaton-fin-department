# Repository Coverage



| Name                                                                    |    Stmts |     Miss |   Cover |   Missing |
|------------------------------------------------------------------------ | -------: | -------: | ------: | --------: |
| src/\_\_init\_\_.py                                                     |        0 |        0 |    100% |           |
| src/config/\_\_init\_\_.py                                              |        0 |        0 |    100% |           |
| src/config/constants.py                                                 |        9 |        0 |    100% |           |
| src/config/settings.py                                                  |       39 |        0 |    100% |           |
| src/core/\_\_init\_\_.py                                                |        0 |        0 |    100% |           |
| src/core/analytics/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| src/core/analytics/assessment\_evidence.py                              |       21 |        1 |     95% |        32 |
| src/core/analytics/assessment\_policy.py                                |       23 |        0 |    100% |           |
| src/core/analytics/enums.py                                             |       66 |        0 |    100% |           |
| src/core/analytics/exceptions.py                                        |       17 |        0 |    100% |           |
| src/core/analytics/schemas.py                                           |      191 |       34 |     82% |51, 55, 61, 63, 70, 76, 83, 88, 107, 109, 384, 413, 417, 419, 429, 440-442, 444-453, 459, 461, 469, 483, 507, 539, 550, 566, 581, 587, 592, 606, 611 |
| src/core/analytics/storages.py                                          |       32 |        0 |    100% |           |
| src/core/analytics/use\_cases.py                                        |       70 |        6 |     91% |48-49, 100-106 |
| src/core/exceptions.py                                                  |        5 |        0 |    100% |           |
| src/core/metrics.py                                                     |       18 |        0 |    100% |           |
| src/core/pets/\_\_init\_\_.py                                           |        0 |        0 |    100% |           |
| src/core/pets/schemas.py                                                |        7 |        0 |    100% |           |
| src/core/pets/storages.py                                               |        5 |        0 |    100% |           |
| src/core/pets/use\_cases.py                                             |       15 |        1 |     93% |        24 |
| src/core/profiles/\_\_init\_\_.py                                       |        0 |        0 |    100% |           |
| src/core/profiles/exceptions.py                                         |        7 |        0 |    100% |           |
| src/core/profiles/schemas.py                                            |       59 |        8 |     86% |23-24, 61, 63, 65, 68-69, 72 |
| src/core/profiles/storages.py                                           |       12 |        0 |    100% |           |
| src/core/profiles/use\_cases.py                                         |       26 |        0 |    100% |           |
| src/core/rewards/\_\_init\_\_.py                                        |        0 |        0 |    100% |           |
| src/core/rewards/exceptions.py                                          |       23 |        0 |    100% |           |
| src/core/rewards/schemas.py                                             |       74 |       13 |     82% |24, 34, 37-38, 55-56, 58, 60, 129, 132, 141, 146-147 |
| src/core/rewards/storages.py                                            |       27 |        0 |    100% |           |
| src/core/rewards/use\_cases.py                                          |       87 |        8 |     91% |71-73, 76, 111, 125, 162-164 |
| src/core/snapshots/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| src/core/snapshots/exceptions.py                                        |       13 |        0 |    100% |           |
| src/core/snapshots/schemas.py                                           |      170 |       14 |     92% |29, 38, 44, 71, 78-81, 167, 183, 239-240, 246, 266 |
| src/core/snapshots/storages.py                                          |       16 |        0 |    100% |           |
| src/core/snapshots/use\_cases.py                                        |       46 |        1 |     98% |        55 |
| src/core/use\_case.py                                                   |        5 |        0 |    100% |           |
| src/di/\_\_init\_\_.py                                                  |        0 |        0 |    100% |           |
| src/di/container.py                                                     |       11 |        0 |    100% |           |
| src/di/providers/\_\_init\_\_.py                                        |        0 |        0 |    100% |           |
| src/di/providers/analytics.py                                           |       11 |        0 |    100% |           |
| src/di/providers/general.py                                             |       14 |        2 |     86% |    12, 16 |
| src/di/providers/pets.py                                                |        8 |        1 |     88% |        15 |
| src/di/providers/postgres.py                                            |       39 |        4 |     90% | 26-28, 32 |
| src/di/providers/profiles.py                                            |        8 |        0 |    100% |           |
| src/di/providers/rewards.py                                             |       14 |        0 |    100% |           |
| src/di/providers/snapshots.py                                           |       11 |        0 |    100% |           |
| src/infra/\_\_init\_\_.py                                               |        0 |        0 |    100% |           |
| src/infra/api/\_\_init\_\_.py                                           |        0 |        0 |    100% |           |
| src/infra/api/analytics/\_\_init\_\_.py                                 |        0 |        0 |    100% |           |
| src/infra/api/analytics/endpoints.py                                    |       16 |        0 |    100% |           |
| src/infra/api/analytics/schemas.py                                      |       52 |        2 |     96% |     54-55 |
| src/infra/api/app.py                                                    |       29 |        0 |    100% |           |
| src/infra/api/boundary.py                                               |       17 |        0 |    100% |           |
| src/infra/api/common/\_\_init\_\_.py                                    |        0 |        0 |    100% |           |
| src/infra/api/common/endpoints.py                                       |        5 |        0 |    100% |           |
| src/infra/api/exceptions.py                                             |       26 |        1 |     96% |        53 |
| src/infra/api/parents/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| src/infra/api/parents/endpoints.py                                      |       12 |        0 |    100% |           |
| src/infra/api/parents/schemas.py                                        |       18 |        0 |    100% |           |
| src/infra/api/parents/skill\_content.py                                 |       50 |        0 |    100% |           |
| src/infra/api/pets/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| src/infra/api/pets/endpoints.py                                         |       10 |        0 |    100% |           |
| src/infra/api/pets/schemas.py                                           |       11 |        0 |    100% |           |
| src/infra/api/profiles/\_\_init\_\_.py                                  |        0 |        0 |    100% |           |
| src/infra/api/profiles/endpoints.py                                     |       11 |        0 |    100% |           |
| src/infra/api/profiles/schemas.py                                       |       15 |        0 |    100% |           |
| src/infra/api/rewards/\_\_init\_\_.py                                   |        0 |        0 |    100% |           |
| src/infra/api/rewards/endpoints.py                                      |       21 |        0 |    100% |           |
| src/infra/api/rewards/schemas.py                                        |       49 |        0 |    100% |           |
| src/infra/api/routers.py                                                |       18 |        0 |    100% |           |
| src/infra/api/snapshots/\_\_init\_\_.py                                 |        0 |        0 |    100% |           |
| src/infra/api/snapshots/endpoints.py                                    |       16 |        0 |    100% |           |
| src/infra/api/snapshots/schemas.py                                      |       25 |        0 |    100% |           |
| src/infra/migrations/\_\_init\_\_.py                                    |        0 |        0 |    100% |           |
| src/infra/migrations/commands.py                                        |       12 |        0 |    100% |           |
| src/infra/migrations/env.py                                             |       40 |        9 |     78% |25-29, 36-43, 74 |
| src/infra/migrations/versions/0001\_create\_pets.py                     |       11 |        0 |    100% |           |
| src/infra/migrations/versions/0002\_create\_snapshots.py                |       13 |        0 |    100% |           |
| src/infra/migrations/versions/0003\_create\_profiles.py                 |       13 |        0 |    100% |           |
| src/infra/migrations/versions/0004\_create\_analytics.py                |       22 |        0 |    100% |           |
| src/infra/migrations/versions/0005\_parent\_rewards.py                  |       15 |        0 |    100% |           |
| src/infra/migrations/versions/0006\_reward\_application\_id\_text.py    |       11 |        0 |    100% |           |
| src/infra/migrations/versions/0007\_analytics\_history\_ranges.py       |       40 |        4 |     90% |47, 56, 91-92 |
| src/infra/migrations/versions/0008\_analytics\_projection\_revisions.py |       21 |        0 |    100% |           |
| src/infra/migrations/versions/\_\_init\_\_.py                           |        0 |        0 |    100% |           |
| src/infra/observability/\_\_init\_\_.py                                 |        0 |        0 |    100% |           |
| src/infra/observability/aggregation.py                                  |       49 |        0 |    100% |           |
| src/infra/observability/business\_metrics.py                            |      349 |       28 |     92% |199, 674, 677-683, 693, 696-699, 702, 705-708, 718, 721, 724, 727, 730, 733, 736-738 |
| src/infra/observability/metrics.py                                      |       14 |        0 |    100% |           |
| src/infra/observability/tracing.py                                      |       12 |        0 |    100% |           |
| src/infra/storages/\_\_init\_\_.py                                      |        0 |        0 |    100% |           |
| src/infra/storages/postgres/\_\_init\_\_.py                             |        0 |        0 |    100% |           |
| src/infra/storages/postgres/analytics\_storage.py                       |       51 |        0 |    100% |           |
| src/infra/storages/postgres/config.py                                   |        4 |        0 |    100% |           |
| src/infra/storages/postgres/models.py                                   |      157 |        1 |     99% |       258 |
| src/infra/storages/postgres/pet\_storage.py                             |       12 |        0 |    100% |           |
| src/infra/storages/postgres/profile\_storage.py                         |       23 |        0 |    100% |           |
| src/infra/storages/postgres/rewards\_storage.py                         |       46 |        1 |     98% |        84 |
| src/infra/storages/postgres/snapshot\_storage.py                        |       27 |        0 |    100% |           |
| **TOTAL**                                                               | **2542** |  **139** | **95%** |           |


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