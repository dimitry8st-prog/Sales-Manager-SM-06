"""SM-06: choose a trusted language and delegate exact materialisation to F130.

This module performs no I/O. Evidence is already normalised by a trusted
producer; locale syntax is checked here, but its provenance is not certified.
The authoring packs and this selection never grant outbound permission.
"""
import re

import sales_first_binding as _binding
import sales_language_registry as _registry
import sales_runtime_materialization as _runtime


_DEFAULT_LOCALE = "en-GB"
_EVIDENCE_PRIORITY = (
    "explicit_recipient_preference",
    "substantive_reply_language",
    "verified_company_business_language",
)
_LOCALE_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)*")


class SM06LanguageError(ValueError):
    """Contract failure containing only a safe machine-readable code."""

    @property
    def code(self):
        return self.args[0]

    def __str__(self):
        return self.code


def _validate_inputs(loaded_registry, binding_config, evidence):
    # Validate every evidence value before applying priority. A malformed
    # lower-priority value must not hide behind a valid explicit preference.
    if (
        type(loaded_registry) is not dict
        or type(binding_config) is not dict
        or type(evidence) is not dict
        or set(evidence) != set(_EVIDENCE_PRIORITY)
    ):
        raise SM06LanguageError("INVALID_INPUT")

    for value in evidence.values():
        if value is not None and not (
            type(value) is str
            and 1 <= len(value) <= 64
            and _LOCALE_PATTERN.fullmatch(value) is not None
        ):
            raise SM06LanguageError("INVALID_INPUT")


def select_language(loaded_registry, binding_config, *, now, evidence):
    """Return the exact selection shape without mutating or saving inputs.

    Validation order is part of CONTRACT.md: evidence roots/shape/values,
    real F105 binding, real F106 registry, scope agreement, then availability.
    A selected unsupported locale fails closed; only absent evidence defaults.
    """
    _validate_inputs(loaded_registry, binding_config, evidence)

    # F105 owns binding/now validation and normalisation. Its original exception
    # is deliberately allowed to pass through unchanged.
    binding = _binding.validate_first_binding(binding_config, now=now)

    # Missing default_locale must reach the real F106 shape validation instead
    # of causing KeyError in this adapter. The sentinel is never a fallback.
    _registry.build_policy_language_fields(
        loaded_registry,
        locale=loaded_registry.get("default_locale", ""),
    )

    if (
        binding["default_locale"] != loaded_registry["default_locale"]
        or binding["language_pack_versions"]
        != loaded_registry["language_pack_versions"]
        or loaded_registry["default_locale"] != _DEFAULT_LOCALE
    ):
        raise SM06LanguageError("LANGUAGE_SCOPE_MISMATCH")

    locale, source = _DEFAULT_LOCALE, "default"
    for field in _EVIDENCE_PRIORITY:
        if evidence[field] is not None:
            locale, source = evidence[field], field
            break

    if (
        locale not in loaded_registry["active_locales"]
        or locale not in binding["allowed_locales"]
    ):
        raise SM06LanguageError("SELECTED_LOCALE_UNAVAILABLE")

    return {
        "schema_version": "SM06_LANGUAGE_SELECTION_V1",
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
    """Select, then call the real F130 chain with unchanged remaining inputs.

    F130 owns F120 binding, F122 exact text, consumer checks and the single
    callback. No exception wrapping, retry, translation or post-error fallback.
    Its return value (including callback-result identity) is returned as is.
    """
    selection = select_language(
        loaded_registry, binding_config, now=now, evidence=evidence
    )
    return _runtime.prepare_bound_materials(
        loaded_registry,
        binding_config,
        now=now,
        locale=selection["locale"],
        required_template_id=required_template_id,
        pinned_pack_version=pinned_pack_version,
        save_materials=save_materials,
    )
