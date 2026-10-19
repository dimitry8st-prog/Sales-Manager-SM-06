# Трассировка SM-06 R1

Формат строки: требование → место → тест → ожидаемый результат → доказательство.

Доказательство `PASS` означает воспроизведённый запуск из `return/logs`. `NOT_RUN` означает, что проверка сознательно не выполнялась.

| Требование | Место | Тест | Ожидаемый результат | Доказательство |
|---|---|---|---|---|
| Защищённые байты целы | `PACKAGE_CHECK.py` | сверка 55 хешей | PASS, выход 0 | PASS, `package_check.exit` и `clean_package_check.exit` |
| Регрессия F105–F130 | `acceptance/run.py cp0` | 152 теста reference | выход 0, без пропусков | PASS, `cp0.exit`, `clean_cp0.exit` |
| Пять пакетов, пять видов, пустые факты, непустые тема и текст | `candidate/packs/*.json` | `test_pack_shape_all5_kinds_and_no_fact_claim_ids` | 25 шаблонов приняты F106 | PASS, `cp1.stderr` |
| 25 проходов F106→F120→F122→F130, один callback, те же входы | `prepare_language_materials` | `test_all25_actual_chain_exact_once_immutable` и `test_chain_matches_real_f130_and_returns_callback_identity` | материал совпал, результат callback тот же объект | PASS, `cp1.stderr` |
| Приоритет свидетельств и английский fallback | `select_language` | `test_selection_priority_and_default`, `test_priority_then_default_and_fresh_result` | `uk-UA`, затем `da-DK`, затем `es-ES`, затем `en-GB` / `default` | PASS, `cp1.stderr` |
| Явный неподдержанный язык без подмены | `select_language` | `test_explicit_unavailable_no_downgrade_zero_save`, `test_explicit_unsupported_does_not_fall_through` | `SELECTED_LOCALE_UNAVAILABLE`, 0 callback | PASS, `cp1.stderr` |
| Чужое поле, страна и плохой корень evidence | проверка входа | `test_invalid_evidence_country_mixed_unknown_zero_save`, `test_bad_roots_and_country_field_before_dependencies` | `INVALID_INPUT`, 0 callback | PASS, `cp1.stderr` |
| `mixed` и `unknown` не считаются классификатором | формат locale id F106 | `test_invalid_evidence_country_mixed_unknown_zero_save` | `SELECTED_LOCALE_UNAVAILABLE` | PASS, `cp1.stderr` |
| Другой регистр локали остаётся другим идентификатором | `select_language` | `test_case_and_malformed_locale_stay_closed` | `en-gb` недоступен, `en-GB ` — `INVALID_INPUT` | PASS, `cp1.stderr` |
| Расхождение default или версий | сверка после F105 и F106 | `test_registry_binding_scope_mismatch` | `LANGUAGE_SCOPE_MISMATCH` | PASS, `cp1.stderr` |
| Совпавший default, отличный от `en-GB` | та же сверка | `test_matching_non_english_default_is_scope_mismatch` | `LANGUAGE_SCOPE_MISMATCH` | PASS, `cp1.stderr` |
| Сдвиг версии, отсутствующий шаблон, пустой текст | настоящий F130 | `test_drift_missing_blank_zero_save_passthrough`, `test_pinned_version_is_not_replaced_before_f130` | тот же тип и текст ошибки, 0 callback | PASS, `cp1.stderr` |
| Сломанный реестр без `KeyError` | `build_policy_language_fields` | `test_malformed_registry_no_raw_keyerror`, `test_missing_default_is_registry_error_not_keyerror` | `LanguageRegistryError`, 0 callback | PASS, `cp1.stderr` |
| Неодобренный факт, пустая тема, наивное время | F106, `validate_materials`, F105 | `test_unapproved_fact_blank_subject_invalid_now_zero_save`, `test_naive_now_and_outbound_pass_through` | исходная ошибка зависимости | PASS, `cp1.stderr` |
| Запрещённый режим отправки | F105 | `test_naive_now_and_outbound_pass_through` | `FirstBindingError('OUTBOUND_MODE_FORBIDDEN')` | PASS, `cp1.stderr` |
| Ошибка зависимости тем же объектом | настоящий F130 | `test_dependency_exception_identity` | тот же `RuleViolation`, 0 callback | PASS, `cp1.stderr` |
| Английский default исчез из привязки | F105 до выбора | `test_unavailable_english_default_rejects` | `FirstBindingError`, 0 callback | PASS, `cp1.stderr` |
| Сбой callback без повтора | F130 | `test_callback_exception_identity_and_no_retry`, `test_callback_failure_is_not_retried` | тот же объект исключения, ровно один вызов | PASS, `cp1.stderr` |
| Отказ выбора до сохранения | `prepare_language_materials` | `test_selection_failure_makes_zero_saves` | 0 callback | PASS, `cp1.stderr` |
| Новая локаль без правки перечисления | данные реестра | `test_synthetic_extra_locale_no_hardcoded_enum`, `test_synthetic_locale_needs_no_enum_edit` | выбираются `de-DE` и `fr-FR` | PASS, `cp1.stderr` |
| Повторный вызов даёт равный новый словарь | `select_language` | `test_priority_then_default_and_fresh_result` | значения равны, объекты разные, входы те же | PASS, `cp1.stderr` |
| Unicode и различие языков | тексты пакетов | `test_same_intent_shape_across_five_languages` | пять разных текстов одного вида; украинские `іїєґ`; датские `æøå`; испанские диакритики | PASS, `cp1.stderr` |
| Одинаковое намерение пяти видов | авторские тексты и `INTENT` в тесте | `test_same_intent_shape_across_five_languages` | одинаковые идентификаторы и виды, пустые факты, без знаков валют | PASS как структурная самопроверка. Независимый языковой отзыв: NOT_RUN |
| Импорты только из стандартной библиотеки и замороженных модулей | `first_sm06_language.py` | `test_module_imports_only_stdlib_and_frozen_dependencies` | `re`, F105, F106, F130 | PASS, `cp1.stderr` |
| Reference EN/RU не изменены | `reference/**` | хеши манифеста | байты исходного ZIP | PASS, `PACKAGE_CHECK` и чистая база |
| Частичное сохранение и отсутствие повтора | граница callback | тесты нуля и одного вызова | до сохранения 0 вызовов; сбой callback останавливает цепочку | PASS, `cp1.stderr` |
| Транзакции, конкуренция, база, очередь, Make, отправка | вне ABI компонента | живой контур не предусмотрен | компонент не обращается к внешним системам | NOT_RUN как живой контур |
| Доверенные источники evidence, кампанийные факты, полная цепочка SM-06, SM-03, установка и откат на рабочем контуре | `INTEGRATION.md` | отдельные ворота владельца | компонентный ZIP их не закрывает | NOT_RUN |
| Публикация GitHub | репозиторий `dimitry8st-prog/Sales-Manager-SM-06` | не входит в инструкцию ZIP | содержимое GitHub не менялось | NOT_RUN |
