# SM-06 R1 — контракт компонента

## Источники и происхождение
Оригинальный SM-06: reference/config/sales_manager_engineering_tasks.json; acceptance: «Приоритет языка и английский fallback проходят через письма, материалы, ответы и QA»; depends_on SM-03. Target policy: default=en-GB, explicit_recipient_preference → substantive_reply_language → verified_company_business_language → default; country alone not sufficient; runtime_applied=false. Сохранённое approved Ukrainian checkpoint 20261018: сохранить EN/RU; текущая команда владельца: включить украинский. UI в snapshot не найден; создание UI и classifier сюда не включены.

Ниже новый тонкий ABI — инженерное извлечение существующего требования, а не утверждение о ранее существовавшем production API. Проверяется до выдачи пакета. Решение непредоставлено: candidate/first_sm06_language.py отсутствует.

## Новый ABI
Модуль first_sm06_language (candidate/first_sm06_language.py).

SM06LanguageError(ValueError): .code — безопасный код; str(error)==code, без текста входов.

select_language(loaded_registry, binding_config, *, now, evidence) -> dict ровно {schema_version:'SM06_LANGUAGE_SELECTION_V1',locale:str,source:str}.

prepare_language_materials(loaded_registry, binding_config, *, now, evidence, required_template_id, pinned_pack_version, save_materials) -> исходный результат save_materials как есть.

Evidence — dict с ровно тремя ключами explicit_recipient_preference, substantive_reply_language, verified_company_business_language. Каждое значение None либо точный locale_id в формате F106. Это trusted normalized evidence, не сырой текст. Нельзя интерпретировать country, TLD, UI locale, алфавит, имя, телефон или подсказку модели. Подтверждение происхождения свидетельств выполняет интегратор, этот pure ABI не создаёт trust из входного dict.

## Порядок
1. Неверные root-типы evidence/loaded_registry/binding_config, fieldset или value evidence -> SM06LanguageError('INVALID_INPUT'). Формат locale_id как в F106: 1..64 символа, [A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*; case не меняется. now проверяет настоящий F105.
2. Вызвать настоящий validate_first_binding(binding_config, now=now). Исходные ошибки не оборачивать.
3. Полная ревалидация loaded_registry настоящим build_policy_language_fields(loaded_registry, locale=loaded_registry['default_locale']); некорректный loaded shape перед этим -> исходная LanguageRegistryError через реальную F106-валидацию, никаких raw KeyError. Проверить точное равенство default_locale и language_pack_versions между binding и registry; несовпадение -> SM06LanguageError('LANGUAGE_SCOPE_MISMATCH'). Default=en-GB требуется этим продуктовым контрактом; иное -> LANGUAGE_SCOPE_MISMATCH.
4. Выбрать первый non-None evidence в порядке policy. Source — ровно имя выбранного ключа. Если все None: locale=en-GB, source='default'. Для выбранной локали потребовать членство и active_locales registry, и allowed_locales binding. Недоступная выбранная локаль -> SM06LanguageError('SELECTED_LOCALE_UNAVAILABLE'). Не переходить ко второму evidence при явном выборе неподдержанной локали; не подменять его английским. Это fail-closed инженерная конкретизация неизвестного source-случая; fallback применяется при отсутствии пригодного языка-свидетельства (upstream обязан передавать None при mixed/unknown; наличие одного украинского слова/кириллицы не свидетельствует о substantive reply language).
5. Не изменять входы; возвращать только selection shape. select_language не выполняет I/O/callback и не выбирает шаблон.
6. prepare_language_materials вызывает select_language, затем настоящий prepare_bound_materials F130 с выбранным locale и остальными аргументами без изменения. Не копировать реализацию F130, не заменять её mock или альтернативным renderer. pinned_pack_version — версия выбранного пакета, не версия preferred до выбора. Исходные ошибки F130/F120/F122/F105/F106/consumer и callback проходят без оборачивания. На любом отказе до save -> 0 callbacks. На успех -> 1 callback с точным материалом F122; результат callback вернуть по identity. Не выполнять перевод, интерполяцию, нормализацию пробелов, повторную отправку либо fallback после drift/ошибки.

## Существующие API — immutable
F106 sales_language_registry: validate_language_pack(pack, *, approved_fact_ids); load_language_registry(registry,packs,*,approved_fact_ids); build_policy_language_fields(loaded,*,locale).
F105 sales_first_binding: validate_first_binding(config,*,now).
F120 sales_action_locale: bind_action_locale(loaded_registry,binding_config,*,now,locale,required_template_id,pinned_pack_version).
F122 sales_template_materialization: materialize_bound_template(loaded_registry,bound_language,*,template_id).
F130 sales_runtime_materialization: prepare_bound_materials(loaded_registry,binding_config,*,now,locale,required_template_id,pinned_pack_version,save_materials).
Точные shapes/error precedence — docstrings и полные source в reference. Ошибки прежних методов не переопределять.

## Acceptance
Все исходные regression PASS без skips; CP1 не пустой. Пять языков × пять kinds через настоящие F106→F120→F122→F130, точный текст и версии, Unicode, повторяемость, input immutability, callback count и exception identity. Проверить policy priority, None/mixed/unknown upstream, unsupported selected, invalid evidence, unavailable default, версии/binding drift, missing template, unapproved facts, blank subject/body, callback failure. Country-only input запрещён точным evidence fieldset. EN/RU прежние fixtures и default не менять. Дополнительный синтетический язык должен работать без enum правки компонента; authoring deliverables остаются пять локалей. Семантическую локализацию оценивает независимый reviewer; структурный harness сам по себе её не доказывает.
