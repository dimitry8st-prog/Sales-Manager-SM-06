# -*- coding: utf-8 -*-
"""Дополнительные проверки SM-06: смысл пакетов, отказы и граница F130."""

import ast
import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "candidate"), str(ROOT / "reference")]

import first_sm06_language as impl
from sales_first_binding import FirstBindingError, validate_first_binding
from sales_language_registry import LanguageRegistryError, load_language_registry
from sales_runtime_materialization import prepare_bound_materials

LOCALES = ["en-GB", "ru-RU", "es-ES", "da-DK", "uk-UA"]
FIELDS = [
    "explicit_recipient_preference",
    "substantive_reply_language",
    "verified_company_business_language",
]
KINDS = {
    "initial": "INITIAL",
    "question": "QUESTION",
    "objection": "OBJECTION",
    "followup": "FOLLOWUP",
    "handoff": "HANDOFF",
}
# Один и тот же замысел каждого вида. Это авторская сверка, не независимый QA.
INTENT = {
    "initial": "нейтральное первое сообщение и приглашение ответить",
    "question": "один уточняющий вопрос без предположения об ответе",
    "objection": "сомнение отмечено, итог не предполагается",
    "followup": "прежнее сообщение остаётся открытым",
    "handoff": "разговор может продолжить человек, без полномочия и решения",
}


def _packs():
    return [
        json.loads((ROOT / "candidate" / "packs" / f"{locale}.json").read_text(encoding="utf-8"))
        for locale in LOCALES
    ]


def _setup():
    fixture = json.loads(
        (ROOT / "reference" / "tests" / "f130" / "fixtures" / "runtime_initial_en.json").read_text(
            encoding="utf-8"
        )
    )
    packs = _packs()
    versions = {pack["locale"]: pack["version"] for pack in packs}
    registry = {
        "schema_version": "FIRST_LANGUAGE_REGISTRY_V1",
        "registry_version": "sm06-test-v1",
        "default_locale": "en-GB",
        "active_locales": LOCALES[:],
        "language_pack_versions": versions,
    }
    loaded = load_language_registry(registry, packs, approved_fact_ids=[])
    binding = fixture["binding_config"]
    binding["allowed_locales"] = LOCALES[:]
    binding["language_pack_versions"] = versions
    now = datetime.fromisoformat(fixture["now"])
    evidence = dict.fromkeys(FIELDS)
    return loaded, binding, now, evidence


class PackSelfCheck(unittest.TestCase):
    def test_same_intent_shape_across_five_languages(self):
        packs = _packs()
        bodies = {locale: {} for locale in LOCALES}
        combined = {locale: "" for locale in LOCALES}
        for pack in packs:
            locale = pack["locale"]
            self.assertEqual(set(pack["templates"]), set(KINDS))
            for template_id, kind in KINDS.items():
                template = pack["templates"][template_id]
                self.assertEqual(template["kind"], kind)
                self.assertEqual(template["locale"], locale)
                self.assertEqual(template["fact_ids"], [])
                self.assertTrue(template["subject"].strip())
                self.assertTrue(template["body"].strip())
                self.assertIn(template_id, INTENT)
                bodies[locale][template_id] = template["body"]
                combined[locale] += template["subject"] + "\n" + template["body"] + "\n"
        for template_id in KINDS:
            texts = [bodies[locale][template_id] for locale in LOCALES]
            self.assertEqual(len(set(texts)), len(LOCALES))
        self.assertTrue(set("абвгдеёжзийклмнопрстуфхцчшщъыьэюя") & set(combined["ru-RU"].casefold()))
        for letter in "іїєґ":
            self.assertIn(letter, combined["uk-UA"].casefold())
        self.assertNotEqual(combined["ru-RU"], combined["uk-UA"])
        for letter in "æøå":
            self.assertIn(letter, combined["da-DK"].casefold())
        self.assertRegex(combined["es-ES"], r"[áéíóúñ¿¡]")
        for text in combined.values():
            lowered = text.casefold()
            for banned in ("€", "$", "£", "gratis", "скидк", "ціна", "precio", " rabat"):
                self.assertNotIn(banned, lowered)

    def test_module_imports_only_stdlib_and_frozen_dependencies(self):
        source = (ROOT / "candidate" / "first_sm06_language.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
        self.assertEqual(
            modules,
            {
                "re",
                "sales_first_binding",
                "sales_language_registry",
                "sales_runtime_materialization",
            },
        )


class SelectLanguage(unittest.TestCase):
    def test_priority_then_default_and_fresh_result(self):
        loaded, binding, now, evidence = _setup()
        for field, locale in zip(FIELDS, ["uk-UA", "da-DK", "es-ES"]):
            evidence[field] = locale
        for field in FIELDS:
            before = copy.deepcopy((loaded, binding, evidence))
            first = impl.select_language(loaded, binding, now=now, evidence=evidence)
            second = impl.select_language(loaded, binding, now=now, evidence=evidence)
            self.assertEqual(
                first,
                {
                    "schema_version": "SM06_LANGUAGE_SELECTION_V1",
                    "locale": evidence[field],
                    "source": field,
                },
            )
            self.assertEqual(first, second)
            self.assertIsNot(first, second)
            self.assertEqual((loaded, binding, evidence), before)
            evidence[field] = None
        before = copy.deepcopy((loaded, binding, evidence))
        self.assertEqual(
            impl.select_language(loaded, binding, now=now, evidence=evidence),
            {
                "schema_version": "SM06_LANGUAGE_SELECTION_V1",
                "locale": "en-GB",
                "source": "default",
            },
        )
        self.assertEqual((loaded, binding, evidence), before)

    def test_explicit_unsupported_does_not_fall_through(self):
        loaded, binding, now, evidence = _setup()
        evidence["explicit_recipient_preference"] = "zz-ZZ"
        evidence["substantive_reply_language"] = "uk-UA"
        with self.assertRaises(impl.SM06LanguageError) as caught:
            impl.select_language(loaded, binding, now=now, evidence=evidence)
        self.assertEqual(caught.exception.code, "SELECTED_LOCALE_UNAVAILABLE")
        self.assertEqual(str(caught.exception), "SELECTED_LOCALE_UNAVAILABLE")
        self.assertNotIn("zz-ZZ", str(caught.exception))

    def test_case_and_malformed_locale_stay_closed(self):
        loaded, binding, now, evidence = _setup()
        evidence["explicit_recipient_preference"] = "en-gb"
        with self.assertRaises(impl.SM06LanguageError) as caught:
            impl.select_language(loaded, binding, now=now, evidence=evidence)
        self.assertEqual(caught.exception.code, "SELECTED_LOCALE_UNAVAILABLE")
        evidence["explicit_recipient_preference"] = "en-GB "
        with self.assertRaises(impl.SM06LanguageError) as caught:
            impl.select_language(loaded, binding, now=now, evidence=evidence)
        self.assertEqual(caught.exception.code, "INVALID_INPUT")

    def test_bad_roots_and_country_field_before_dependencies(self):
        loaded, binding, now, evidence = _setup()
        samples = [
            (None, binding, evidence),
            (loaded, [], evidence),
            (loaded, binding, None),
            (loaded, binding, {}),
            (loaded, binding, dict(evidence, country="UA")),
            (loaded, binding, dict(evidence, explicit_recipient_preference=["uk-UA"])),
        ]
        for registry, config, item in samples:
            with self.assertRaises(impl.SM06LanguageError) as caught:
                impl.select_language(registry, config, now=now, evidence=item)
            self.assertEqual(str(caught.exception), "INVALID_INPUT")

    def test_matching_non_english_default_is_scope_mismatch(self):
        loaded, binding, now, evidence = _setup()
        loaded["default_locale"] = "ru-RU"
        binding["default_locale"] = "ru-RU"
        with self.assertRaises(impl.SM06LanguageError) as caught:
            impl.select_language(loaded, binding, now=now, evidence=evidence)
        self.assertEqual(caught.exception.code, "LANGUAGE_SCOPE_MISMATCH")

    def test_missing_default_is_registry_error_not_keyerror(self):
        loaded, binding, now, evidence = _setup()
        del loaded["default_locale"]
        with self.assertRaises(LanguageRegistryError):
            impl.select_language(loaded, binding, now=now, evidence=evidence)

    def test_naive_now_and_outbound_pass_through(self):
        loaded, binding, now, evidence = _setup()
        naive = now.replace(tzinfo=None)
        with self.assertRaises(FirstBindingError) as caught:
            impl.select_language(loaded, binding, now=naive, evidence=evidence)
        with self.assertRaises(FirstBindingError) as expected:
            validate_first_binding(binding, now=naive)
        self.assertEqual(str(caught.exception), str(expected.exception))
        binding["release_mode"] = "SEND"
        aware = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
        with self.assertRaises(FirstBindingError) as caught:
            impl.select_language(loaded, binding, now=aware, evidence=evidence)
        self.assertEqual(str(caught.exception), "OUTBOUND_MODE_FORBIDDEN")

    def test_synthetic_locale_needs_no_enum_edit(self):
        loaded, binding, now, evidence = _setup()
        locale = "fr-FR"
        pack = copy.deepcopy(loaded["packs_by_locale"]["en-GB"])
        pack["locale"] = locale
        pack["version"] = "synthetic-fr-v1"
        for template in pack["templates"].values():
            template["locale"] = locale
        loaded["active_locales"].append(locale)
        loaded["language_pack_versions"][locale] = pack["version"]
        loaded["packs_by_locale"][locale] = pack
        binding["allowed_locales"].append(locale)
        binding["language_pack_versions"][locale] = pack["version"]
        evidence["explicit_recipient_preference"] = locale
        self.assertEqual(
            impl.select_language(loaded, binding, now=now, evidence=evidence)["locale"],
            locale,
        )


class PrepareMaterials(unittest.TestCase):
    def test_chain_matches_real_f130_and_returns_callback_identity(self):
        loaded, binding, now, evidence = _setup()
        for locale in LOCALES:
            evidence["explicit_recipient_preference"] = locale
            for template_id in KINDS:
                pin = loaded["language_pack_versions"][locale]
                expected = []
                prepare_bound_materials(
                    loaded,
                    binding,
                    now=now,
                    locale=locale,
                    required_template_id=template_id,
                    pinned_pack_version=pin,
                    save_materials=expected.append,
                )
                calls = []
                token = object()
                before = copy.deepcopy((loaded, binding, evidence))

                def save(material):
                    calls.append(material)
                    return token

                result = impl.prepare_language_materials(
                    loaded,
                    binding,
                    now=now,
                    evidence=evidence,
                    required_template_id=template_id,
                    pinned_pack_version=pin,
                    save_materials=save,
                )
                self.assertIs(result, token)
                self.assertEqual(calls, expected)
                self.assertEqual(len(calls), 1)
                self.assertEqual((loaded, binding, evidence), before)

    def test_selection_failure_makes_zero_saves(self):
        loaded, binding, now, evidence = _setup()
        evidence["explicit_recipient_preference"] = "zz-ZZ"
        evidence["substantive_reply_language"] = "da-DK"
        calls = []
        with self.assertRaises(impl.SM06LanguageError):
            impl.prepare_language_materials(
                loaded,
                binding,
                now=now,
                evidence=evidence,
                required_template_id="initial",
                pinned_pack_version=loaded["language_pack_versions"]["en-GB"],
                save_materials=calls.append,
            )
        self.assertEqual(calls, [])

    def test_pinned_version_is_not_replaced_before_f130(self):
        loaded, binding, now, evidence = _setup()
        evidence["explicit_recipient_preference"] = "uk-UA"
        calls = []
        with self.assertRaises(Exception) as caught:
            prepare_bound_materials(
                loaded,
                binding,
                now=now,
                locale="uk-UA",
                required_template_id="initial",
                pinned_pack_version="preferred-before-selection",
                save_materials=calls.append,
            )
        calls.clear()
        with self.assertRaises(type(caught.exception)) as actual:
            impl.prepare_language_materials(
                loaded,
                binding,
                now=now,
                evidence=evidence,
                required_template_id="initial",
                pinned_pack_version="preferred-before-selection",
                save_materials=calls.append,
            )
        self.assertEqual(str(actual.exception), str(caught.exception))
        self.assertEqual(calls, [])

    def test_callback_failure_is_not_retried(self):
        loaded, binding, now, evidence = _setup()
        calls = []
        error = RuntimeError("sentinel")

        def save(material):
            calls.append(material)
            raise error

        with self.assertRaises(RuntimeError) as caught:
            impl.prepare_language_materials(
                loaded,
                binding,
                now=now,
                evidence=evidence,
                required_template_id="handoff",
                pinned_pack_version=loaded["language_pack_versions"]["en-GB"],
                save_materials=save,
            )
        self.assertIs(caught.exception, error)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
