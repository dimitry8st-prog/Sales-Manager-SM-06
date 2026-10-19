# SM-06 R1: языковой компонент

Учебный компонент выбирает язык из уже подтверждённых нормализованных свидетельств и передаёт подготовку материалов настоящему F130. Продуктовый язык по умолчанию — `en-GB`.

## Что реализовано

`first_sm06_language.py` предоставляет точный ABI из `CONTRACT.md`:

- `select_language(loaded_registry, binding_config, *, now, evidence)`;
- `prepare_language_materials(loaded_registry, binding_config, *, now, evidence, required_template_id, pinned_pack_version, save_materials)`;
- `SM06LanguageError(ValueError)` с безопасным `.code` и `str(error) == code`.

Приоритет: `explicit_recipient_preference` → `substantive_reply_language` → `verified_company_business_language`. Только три значения `None` дают `en-GB` с источником `default`. Явно выбранная недоступная локаль вызывает `SELECTED_LOCALE_UNAVAILABLE`: следующий источник не пробуется.

Компонент сначала проверяет все входные evidence, затем вызывает F105, полную ревалидацию F106 и сравнивает default/карты версий. Порядок ошибок сохранён. `now` проверяет F105. Исходные ошибки зависимостей и callback проходят тем же объектом.

`prepare_language_materials` вызывает реальный F130: F120 связывает локаль/версию/шаблон, F122 извлекает точные тексты, consumer проверяет материал, затем callback вызывается один раз. До сохранения при отказе callback не вызывается. Возврат callback сохраняется по identity. Перевода, интерполяции, обрезки пробелов и повторов нет.

## Пакеты и версии

В `candidate/packs/` находятся пять **NONPROD authoring samples**: en-GB, ru-RU, es-ES, da-DK, uk-UA. В каждом пять шаблонов: initial, question, objection, followup, handoff. Версия каждого — `sm06-authoring-v1`; собственные тестовые реестры получают версии из самих JSON, поэтому pin соответствует выбранному пакету. Все subject/body непустые; fact_ids пусты. Существующие reference EN/RU сохранены побайтово.

Тексты — образцы для проверки. Независимая языковая приёмка и разрешение для рассылки не получены. Внутренняя проверка всех 25 пар subject/body: `return/SEMANTIC_REVIEW.md`.

Выбор языка не содержит enum пяти локалей: дополнительная корректная локаль работает через реестр без правки компонента. Поставляемых authoring-пакетов ровно пять.

## Запуск проверок

Из корня пакета с Python 3.12:

```sh
python -B PACKAGE_CHECK.py
python -B acceptance/run.py cp0
python -B acceptance/run.py cp1
```

CP0 запускает шесть исходных suites. CP1 запускает frozen acceptance и собственные тесты. Фактические результаты и коды выхода находятся в `return/REPORT.md` и сырых логах; этот README не подменяет их.

Для двух чистых прогонов и сборки из checkout репозитория:

```sh
python -B SM06_Dmitry_R1/return/verify_sm06.py --repo .
```

Скрипт использует сохранённый исходный ZIP в корне репозитория. У возвращённого ZIP другой сценарий: распаковать и выполнить три прямые команды выше.

## Подключение и восстановление

Интегратор добавляет `candidate/` и неизменённый `reference/` в путь импорта, загружает пакеты настоящим `load_language_registry`, передаёт согласованный binding и pin выбранного пакета. `save_materials` в тестах — только локальный recorder.

Evidence должен поступать от доверенного producer: каждая из трёх позиций — `None` либо точный locale_id. Для mixed/unknown producer обязан передать `None`. Строки `mixed` и `unknown` здесь не специальные флаги. По стране, алфавиту или сырому ответу компонент язык не угадывает; доверенность происхождения dict он не устанавливает.

Активация runtime, production registry, факты, реальные отправки, полная цепочка SM-03/SM-06 и backup/restore общей системы остаются отдельными воротами из `INTEGRATION.md`. Известное ограничение legacy `sales_preparation_contract.py` для ru-RU/D04 здесь не исправляется: этого файла в разрешённой зоне нет.

Для восстановления учебной среды распаковать неизменённый исходный ZIP в новую папку, наложить разрешённые candidate/return файлы и повторить проверки. Production-состояние эта работа не меняет.
