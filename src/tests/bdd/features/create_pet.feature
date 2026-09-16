Feature: Создание питомца

  Scenario: Пользователь создает питомца с начальным балансом
    Given Существующие питомцы
      | id                                   | name   | temper | balance |
      | 11111111-1111-1111-1111-111111111111 | Murzik | calm   | 45      |
    When Создание питомца
      | field  | value                                |
      | id     | 12345678-1234-5678-1234-567812345678 |
      | name   | Barsik                               |
      | temper | playful                              |
    Then Создан питомец
      | field   | value                                |
      | id      | 12345678-1234-5678-1234-567812345678 |
      | name    | Barsik                               |
      | temper  | playful                              |
      | balance | 100                                  |
    And Существующие питомцы
      | id                                   | name   | temper  | balance |
      | 11111111-1111-1111-1111-111111111111 | Murzik | calm    | 45      |
      | 12345678-1234-5678-1234-567812345678 | Barsik | playful | 100     |
    And Питомец передан в хранилище
      | field   | value                                |
      | id      | 12345678-1234-5678-1234-567812345678 |
      | name    | Barsik                               |
      | temper  | playful                              |
      | balance | 100                                  |
