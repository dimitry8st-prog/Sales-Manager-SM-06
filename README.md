# Sales Manager FIRST — SM-06, локальный возврат Cursor

Эта ветка публикует работу из локальной папки `SM06_Dmitry_R1`. Ветка `main` содержит другой уже проверенный возврат и этой публикацией не заменяется.

Компонент выбирает язык по нормализованным свидетельствам и передаёт шаблон в настоящий F130. Локали пакетов: en-GB, ru-RU, es-ES, da-DK, uk-UA. Полный SM-06 и живая отправка этой веткой не закрываются.

Проверено локально на Python 3.12.8:

| Команда | Результат |
|---|---|
| `python -B PACKAGE_CHECK.py` | PASS, 55 защищённых файлов |
| `python -B acceptance/run.py cp0` | 152 теста, выход 0 |
| `python -B acceptance/run.py cp1` | 13 замороженных и 14 собственных тестов, выход 0 |

Архив с одной корневой папкой `SM06_Dmitry_R1`: [artifacts/SM06_Dmitry_R1_RETURN.zip](artifacts/SM06_Dmitry_R1_RETURN.zip). SHA-256: `f6fe6b1be992d395d9a0a264e878f086347d96fc0dcfb518f0cde83fdc047aef`.

Документы: [REPORT.md](SM06_Dmitry_R1/return/REPORT.md), [TRACEABILITY.md](SM06_Dmitry_R1/return/TRACEABILITY.md), журналы в [return/logs](SM06_Dmitry_R1/return/logs).
