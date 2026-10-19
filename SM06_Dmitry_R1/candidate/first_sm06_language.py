# -*- coding: utf-8 -*-
"""Выбор языка SM-06 и передача шаблона в настоящий F130.

Модуль не переводит текст, не угадывает язык по стране или алфавиту и не
сохраняет материалы сам. Доверие к свидетельствам подтверждает интегратор:
сюда приходит уже нормализованный словарь из трёх полей.

Порядок select_language зафиксирован контрактом:

1. Корневые типы, набор полей evidence и значения локалей.
2. Настоящий validate_first_binding. Его ошибка не оборачивается.
3. Настоящий build_policy_language_fields повторно проверяет реестр.
4. default и карта версий привязки совпадают с реестром, default равен en-GB.
5. Первое непустое свидетельство. Пустой набор даёт en-GB / default.
   Неподдержанная выбранная локаль останавливает выбор.
"""

import re

from sales_first_binding import validate_first_binding
from sales_language_registry import build_policy_language_fields
from sales_runtime_materialization import prepare_bound_materials

_SCHEMA = "SM06_LANGUAGE_SELECTION_V1"
_DEFAULT_LOCALE = "en-GB"
_EVIDENCE_FIELDS = (
    "explicit_recipient_preference",
    "substantive_reply_language",
    "verified_company_business_language",
)
# Тот же locale_id, что у F106: длина 1..64, регистр сохраняется.
_LOCALE_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*")


class SM06LanguageError(ValueError):
    """Ошибка выбора языка: наружу выходит только стабильный код."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)

    def __str__(self):
        return self.args[0]


def _fail(code):
    raise SM06LanguageError(code)


def _is_locale(value):
    return (
        isinstance(value, str)
        and 1 <= len(value) <= 64
        and _LOCALE_RE.fullmatch(value) is not None
    )


def _require_evidence(evidence):
    """Принять только точный словарь трёх свидетельств."""
    if type(evidence) is not dict or set(evidence) != set(_EVIDENCE_FIELDS):
        _fail("INVALID_INPUT")
    for field in _EVIDENCE_FIELDS:
        value = evidence[field]
        if value is not None and not _is_locale(value):
            _fail("INVALID_INPUT")


def _revalidate_registry(loaded_registry):
    """Прогнать loaded-реестр через настоящий F106 без сырого KeyError.

    Отсутствующий default_locale нельзя читать напрямую. В F106 тогда
    передаётся служебный аргумент en-GB, а отказ формы остаётся ошибкой F106.
    """
    if type(loaded_registry) is dict and "default_locale" in loaded_registry:
        query_locale = loaded_registry["default_locale"]
    else:
        query_locale = _DEFAULT_LOCALE
    build_policy_language_fields(loaded_registry, locale=query_locale)


def select_language(loaded_registry, binding_config, *, now, evidence):
    """Выбрать локаль и имя источника. Входы не изменяются."""
    if type(loaded_registry) is not dict or type(binding_config) is not dict:
        _fail("INVALID_INPUT")
    _require_evidence(evidence)

    binding = validate_first_binding(binding_config, now=now)
    _revalidate_registry(loaded_registry)

    versions_match = (
        binding["language_pack_versions"] == loaded_registry["language_pack_versions"]
    )
    if (
        binding["default_locale"] != loaded_registry["default_locale"]
        or loaded_registry["default_locale"] != _DEFAULT_LOCALE
        or not versions_match
    ):
        _fail("LANGUAGE_SCOPE_MISMATCH")

    locale = None
    source = None
    for field in _EVIDENCE_FIELDS:
        if evidence[field] is not None:
            locale = evidence[field]
            source = field
            break
    if locale is None:
        locale = _DEFAULT_LOCALE
        source = "default"
    if (
        locale not in loaded_registry["active_locales"]
        or locale not in binding["allowed_locales"]
    ):
        _fail("SELECTED_LOCALE_UNAVAILABLE")

    return {
        "schema_version": _SCHEMA,
        "locale": locale,
        "source": source,
    }


def prepare_language_materials(
    loaded_registry,
    binding_config,
    *,
    now,
    evidence,
    required_template_id,
    pinned_pack_version,
    save_materials,
):
    """Выбрать язык и один раз передать шаблон в настоящий F130.

    pinned_pack_version не заменяется версией предпочтения до выбора.
    Ошибка выбора происходит до callback. Ошибки F130 и callback выходят
    исходными объектами, без повтора и без запасного языка.
    """
    selection = select_language(
        loaded_registry,
        binding_config,
        now=now,
        evidence=evidence,
    )
    return prepare_bound_materials(
        loaded_registry,
        binding_config,
        now=now,
        locale=selection["locale"],
        required_template_id=required_template_id,
        pinned_pack_version=pinned_pack_version,
        save_materials=save_materials,
    )
