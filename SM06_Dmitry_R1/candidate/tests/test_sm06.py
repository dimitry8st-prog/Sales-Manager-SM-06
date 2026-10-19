"""Independent regression tests for the SM-06 candidate.

The positive materialization paths use the issued F105/F106/F120/F122/F130
components. Mocks are limited to fault injection and detection of forbidden I/O.
No network, database, delivery, or production facts are involved.
"""

import copy
import inspect
import json
import os
import sys
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "candidate"), str(ROOT / "reference")]

import first_sm06_language as candidate
import sales_first_binding as f105
import sales_language_registry as f106
import sales_runtime_materialization as f130
from sales_action_locale import ActionLocaleError
from sales_first_binding import FirstBindingError
from sales_language_registry import LanguageRegistryError
from sales_rules import RuleViolation
from sales_template_materialization import TemplateMaterializationError

LOCALES = ("en-GB", "ru-RU", "es-ES", "da-DK", "uk-UA")
FIELDS = (
    "explicit_recipient_preference",
    "substantive_reply_language",
    "verified_company_business_language",
)
KINDS = {
    "initial": "INITIAL",
    "question": "QUESTION",
    "objection": "OBJECTION",
    "followup": "FOLLOWUP",
    "handoff": "HANDOFF",
}


class CandidateLanguageTests(unittest.TestCase):
    def setUp(self):
        fixture = json.loads(
            (ROOT / "reference/tests/f130/fixtures/runtime_initial_en.json")
            .read_text(encoding="utf-8")
        )
        self.packs = [
            json.loads(
                (ROOT / "candidate/packs" / (locale + ".json"))
                .read_text(encoding="utf-8")
            )
            for locale in LOCALES
        ]
        versions = {pack["locale"]: pack["version"] for pack in self.packs}
        registry = {
            "schema_version": "FIRST_LANGUAGE_REGISTRY_V1",
            "registry_version": "candidate-regression-v1",
            "default_locale": "en-GB",
            "active_locales": list(LOCALES),
            "language_pack_versions": versions,
        }
        self.loaded = f106.load_language_registry(
            registry, self.packs, approved_fact_ids=[]
        )
        self.binding = copy.deepcopy(fixture["binding_config"])
        self.binding["allowed_locales"] = list(LOCALES)
        self.binding["language_pack_versions"] = copy.deepcopy(versions)
        self.now = datetime.fromisoformat(fixture["now"])
        self.evidence = dict.fromkeys(FIELDS)

    def select(self, **overrides):
        arguments = {
            "loaded_registry": self.loaded,
            "binding_config": self.binding,
            "now": self.now,
            "evidence": self.evidence,
        }
        arguments.update(overrides)
        return candidate.select_language(**arguments)

    def prepare(self, **overrides):
        arguments = {
            "loaded_registry": self.loaded,
            "binding_config": self.binding,
            "now": self.now,
            "evidence": self.evidence,
            "required_template_id": "initial",
            "pinned_pack_version": None,
            "save_materials": lambda materials: materials,
        }
        arguments.update(overrides)
        return candidate.prepare_language_materials(**arguments)

    def assert_candidate_error(self, code, operation):
        with self.assertRaises(candidate.SM06LanguageError) as caught:
            operation()
        self.assertIsInstance(caught.exception, ValueError)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)
        self.assertEqual(caught.exception.args, (code,))
        return caught.exception

    def add_locale(self, locale, version="synthetic-v1"):
        pack = copy.deepcopy(self.loaded["packs_by_locale"]["en-GB"])
        pack["locale"] = locale
        pack["version"] = version
        for template in pack["templates"].values():
            template["locale"] = locale
        self.loaded["active_locales"].append(locale)
        self.loaded["language_pack_versions"][locale] = version
        self.loaded["packs_by_locale"][locale] = pack
        self.binding["allowed_locales"].append(locale)
        self.binding["language_pack_versions"][locale] = version

    def test_public_signatures_and_error_contract(self):
        self.assertEqual(
            tuple(inspect.signature(candidate.select_language).parameters),
            ("loaded_registry", "binding_config", "now", "evidence"),
        )
        parameters = inspect.signature(
            candidate.prepare_language_materials
        ).parameters
        self.assertEqual(
            tuple(parameters),
            (
                "loaded_registry", "binding_config", "now", "evidence",
                "required_template_id", "pinned_pack_version",
                "save_materials",
            ),
        )
        for name in tuple(parameters)[2:]:
            self.assertEqual(
                parameters[name].kind,
                inspect.Parameter.KEYWORD_ONLY,
            )
        error = candidate.SM06LanguageError("INVALID_INPUT")
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.code, str(error))

    def test_all_priority_combinations_and_exact_result_shape(self):
        choices = (None, "uk-UA", "es-ES")
        for explicit in choices:
            for reply in choices:
                for company in choices:
                    evidence = dict(zip(FIELDS, (explicit, reply, company)))
                    source, locale = next(
                        (
                            (field, evidence[field])
                            for field in FIELDS
                            if evidence[field] is not None
                        ),
                        ("default", "en-GB"),
                    )
                    with self.subTest(evidence=evidence):
                        self.assertEqual(self.select(evidence=evidence), {
                            "schema_version": "SM06_LANGUAGE_SELECTION_V1",
                            "locale": locale,
                            "source": source,
                        })

    def test_all_evidence_fields_validated_before_priority_or_binding(self):
        # An earlier valid preference must not conceal invalid later evidence.
        invalid_values = (
            "", " uk-UA", "uk-UA ", "uk_UA", "-uk", "uk-",
            "uk--UA", "uk\nUA", "українська", "a" * 65,
            True, 0, [], {},
        )
        for field in FIELDS:
            for value in invalid_values:
                evidence = dict.fromkeys(FIELDS)
                evidence[FIELDS[0]] = "uk-UA"
                evidence[field] = value
                with self.subTest(field=field, value=value):
                    self.assert_candidate_error(
                        "INVALID_INPUT",
                        lambda: self.select(
                            evidence=evidence, binding_config={},
                            loaded_registry={}, now=None,
                        ),
                    )

    def test_exact_evidence_fieldset_forbids_country_and_raw_text(self):
        bad_values = (None, [], {}, dict(self.evidence, country="UA"),
                      dict(self.evidence, raw_text="Україна"))
        for evidence in bad_values:
            with self.subTest(evidence=evidence):
                self.assert_candidate_error(
                    "INVALID_INPUT", lambda: self.select(evidence=evidence)
                )
        for field in FIELDS:
            evidence = dict(self.evidence)
            del evidence[field]
            self.assert_candidate_error(
                "INVALID_INPUT", lambda: self.select(evidence=evidence)
            )

    def test_non_dict_root_arguments_fail_before_dependency_checks(self):
        class DictSubclass(dict):
            pass
        for key in ("loaded_registry", "binding_config", "evidence"):
            for bad in (None, [], "not-an-object", DictSubclass()):
                with self.subTest(key=key, value=type(bad).__name__):
                    self.assert_candidate_error(
                        "INVALID_INPUT", lambda: self.select(**{key: bad})
                    )

    def test_locale_id_boundaries_case_and_unknown_are_not_normalized(self):
        for locale in ("a", "a" * 64, "mixed", "unknown", "en-gb"):
            evidence = dict(self.evidence)
            evidence[FIELDS[0]] = locale
            with self.subTest(locale=locale):
                self.assert_candidate_error(
                    "SELECTED_LOCALE_UNAVAILABLE",
                    lambda: self.select(evidence=evidence),
                )
        # A syntactically valid, case-distinct ID can work when actually loaded.
        self.add_locale("en-gb")
        self.evidence[FIELDS[0]] = "en-gb"
        self.assertEqual(self.select()["locale"], "en-gb")

    def test_unsupported_higher_priority_does_not_downgrade_or_save(self):
        for index, field in enumerate(FIELDS):
            evidence = dict.fromkeys(FIELDS)
            evidence[field] = "zz-ZZ"
            for lower in FIELDS[index + 1:]:
                evidence[lower] = "uk-UA"
            calls = []
            with self.subTest(field=field):
                self.assert_candidate_error(
                    "SELECTED_LOCALE_UNAVAILABLE",
                    lambda: self.prepare(
                        evidence=evidence, save_materials=calls.append
                    ),
                )
                self.assertEqual(calls, [])

    def test_first_binding_error_precedes_registry_scope_and_selection(self):
        self.loaded["default_locale"] = None
        self.evidence[FIELDS[0]] = "zz-ZZ"
        self.binding["release_mode"] = "OUTBOUND"
        with self.assertRaises(FirstBindingError) as caught:
            self.select()
        self.assertEqual(caught.exception.code, "OUTBOUND_MODE_FORBIDDEN")

    def test_naive_invalid_and_expired_now_use_real_first_binding(self):
        times = (
            (None, "INVALID_INPUT"),
            (self.now.isoformat(), "INVALID_INPUT"),
            (self.now.replace(tzinfo=None), "INVALID_INPUT"),
            (self.now + timedelta(days=3), "INVALID_VALIDITY"),
        )
        for now, code in times:
            calls = []
            with self.subTest(now=now):
                with self.assertRaises(FirstBindingError) as caught:
                    self.prepare(now=now, save_materials=calls.append)
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(calls, [])

    def test_f106_full_tree_validation_precedes_scope_and_selection(self):
        self.binding["default_locale"] = "ru-RU"
        self.evidence[FIELDS[0]] = "zz-ZZ"
        # The corrupt language is not the selected language or the default.
        self.loaded["packs_by_locale"]["da-DK"]["templates"]["handoff"][
            "body"
        ] = ""
        calls = []
        with self.assertRaises(LanguageRegistryError) as caught:
            self.prepare(save_materials=calls.append)
        self.assertEqual(caught.exception.code, "INVALID_TEMPLATE")
        self.assertEqual(calls, [])

    def test_malformed_loaded_containers_use_f106_not_raw_key_errors(self):
        variants = []
        for key in self.loaded:
            variant = copy.deepcopy(self.loaded)
            del variant[key]
            variants.append(("missing-" + key, variant))
        for key, value in (
            ("packs_by_locale", None),
            ("language_pack_versions", []),
            ("active_locales", []),
            ("default_locale", None),
            ("approved_fact_ids", None),
        ):
            variant = copy.deepcopy(self.loaded)
            variant[key] = value
            variants.append(("wrong-" + key, variant))
        for label, loaded in variants:
            calls = []
            with self.subTest(shape=label):
                with self.assertRaises(LanguageRegistryError):
                    self.prepare(
                        loaded_registry=loaded,
                        save_materials=calls.append,
                    )
                self.assertEqual(calls, [])

    def test_scope_checks_versions_defaults_and_product_english(self):
        for mode in ("versions", "defaults", "product-default"):
            loaded, binding = copy.deepcopy((self.loaded, self.binding))
            if mode == "versions":
                binding["language_pack_versions"]["uk-UA"] = "drift-v1"
            else:
                binding["default_locale"] = "ru-RU"
                if mode == "product-default":
                    loaded["default_locale"] = "ru-RU"
            calls = []
            with self.subTest(mode=mode):
                self.assert_candidate_error(
                    "LANGUAGE_SCOPE_MISMATCH",
                    lambda: self.prepare(
                        loaded_registry=loaded, binding_config=binding,
                        save_materials=calls.append,
                    ),
                )
                self.assertEqual(calls, [])

    def test_missing_default_is_rejected_and_never_silently_replaced(self):
        self.binding["allowed_locales"].remove("en-GB")
        del self.binding["language_pack_versions"]["en-GB"]
        calls = []
        with self.assertRaises(FirstBindingError) as caught:
            self.prepare(save_materials=calls.append)
        self.assertEqual(caught.exception.code, "INVALID_LANGUAGE_CONFIG")
        self.assertEqual(calls, [])

    def test_synthetic_locale_works_through_real_materialization(self):
        # A sixth locale is a test input, not an extra authoring deliverable.
        self.add_locale("de-DE", "de-synthetic-v1")
        self.evidence[FIELDS[1]] = "de-DE"
        calls = []
        token = object()
        def save(materials):
            calls.append(materials)
            return token
        self.assertIs(self.prepare(
            pinned_pack_version="de-synthetic-v1", save_materials=save
        ), token)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["locale"], "de-DE")
        self.assertEqual(
            calls[0]["language_pack_version"], "de-synthetic-v1"
        )
        self.assertEqual(self.select()["source"], FIELDS[1])

    def test_pack_contract_five_kinds_versions_and_no_claim_ids(self):
        self.assertEqual({pack["locale"] for pack in self.packs}, set(LOCALES))
        for pack in self.packs:
            with self.subTest(locale=pack["locale"]):
                self.assertEqual(set(pack), {
                    "schema_version", "locale", "version", "templates"
                })
                self.assertEqual(
                    pack["schema_version"], "FIRST_LANGUAGE_PACK_V1"
                )
                self.assertEqual(set(pack["templates"]), set(KINDS))
                self.assertEqual(
                    pack["version"],
                    self.binding["language_pack_versions"][pack["locale"]],
                )
                for template_id, kind in KINDS.items():
                    template = pack["templates"][template_id]
                    self.assertEqual(set(template), {
                        "kind", "locale", "subject", "body", "fact_ids"
                    })
                    self.assertEqual(template["kind"], kind)
                    self.assertEqual(template["locale"], pack["locale"])
                    self.assertTrue(template["subject"].strip())
                    self.assertTrue(template["body"].strip())
                    self.assertEqual(template["fact_ids"], [])

    def test_all_25_materials_exact_text_versions_callback_identity(self):
        before = copy.deepcopy((self.loaded, self.binding, self.evidence))
        for locale in LOCALES:
            for template_id, kind in KINDS.items():
                evidence = dict.fromkeys(FIELDS)
                evidence[FIELDS[0]] = locale
                calls = []
                token = object()
                def save(materials):
                    calls.append(materials)
                    return token
                with self.subTest(locale=locale, template=template_id):
                    self.assertIs(self.prepare(
                        evidence=evidence,
                        required_template_id=template_id,
                        pinned_pack_version=self.loaded[
                            "language_pack_versions"
                        ][locale],
                        save_materials=save,
                    ), token)
                    template = self.loaded["packs_by_locale"][locale][
                        "templates"
                    ][template_id]
                    self.assertEqual(calls, [{
                        "schema_version": "FIRST_TEMPLATE_MATERIALS_V1",
                        "locale": locale,
                        "language_pack_version": self.loaded[
                            "language_pack_versions"
                        ][locale],
                        "registry_version": self.loaded["registry_version"],
                        "kind": kind,
                        "subject": template["subject"],
                        "body": template["body"],
                        "fact_ids": [],
                        "template_id": template_id,
                    }])
        self.assertEqual(
            (self.loaded, self.binding, self.evidence), before
        )

    def test_selected_pack_pin_not_unselected_preference_pin(self):
        # No recipient preference: select reply language and pin that package.
        self.add_locale("de-DE", "distinct-de-v1")
        self.evidence[FIELDS[1]] = "de-DE"
        self.evidence[FIELDS[2]] = "en-GB"
        calls = []
        with self.assertRaises(ActionLocaleError) as caught:
            self.prepare(
                pinned_pack_version=self.loaded[
                    "language_pack_versions"
                ]["en-GB"],
                save_materials=calls.append,
            )
        self.assertEqual(caught.exception.code, "PACK_VERSION_CHANGED")
        self.assertEqual(calls, [])
        self.prepare(
            pinned_pack_version="distinct-de-v1",
            save_materials=calls.append,
        )
        self.assertEqual(len(calls), 1)

    def test_missing_template_is_not_replaced_and_never_saved(self):
        self.evidence[FIELDS[0]] = "uk-UA"
        calls = []
        with self.assertRaises(ActionLocaleError) as caught:
            self.prepare(
                required_template_id="missing-template",
                save_materials=calls.append,
            )
        self.assertEqual(caught.exception.code, "TEMPLATE_NOT_APPROVED")
        self.assertEqual(calls, [])

    def test_invalid_template_and_pin_ids_are_original_f120_errors(self):
        for key in ("required_template_id", "pinned_pack_version"):
            for value in ("", " bad", [], True):
                calls = []
                with self.subTest(key=key, value=value):
                    with self.assertRaises(ActionLocaleError) as caught:
                        self.prepare(**{key: value,
                                       "save_materials": calls.append})
                    self.assertEqual(caught.exception.code, "INVALID_INPUT")
                    self.assertEqual(calls, [])

    def test_whitespace_unicode_and_template_literals_remain_exact(self):
        template = self.loaded["packs_by_locale"]["uk-UA"][
            "templates"
        ]["initial"]
        template["subject"] = "  Перевірка — і ї є ґ 🙂  "
        template["body"] = (
            "\n  Не інтерполювати {{client}}; café; dansk: æ ø å.\n\t"
        )
        self.evidence[FIELDS[0]] = "uk-UA"
        before = copy.deepcopy((self.loaded, self.binding, self.evidence))
        material = self.prepare()
        self.assertEqual(material["subject"], template["subject"])
        self.assertEqual(material["body"], template["body"])
        self.assertEqual(
            (self.loaded, self.binding, self.evidence), before
        )

    def test_unapproved_fact_and_blank_body_fail_before_save(self):
        for mode in ("unapproved-fact", "blank-body"):
            loaded = copy.deepcopy(self.loaded)
            template = loaded["packs_by_locale"]["uk-UA"][
                "templates"
            ]["initial"]
            template[
                "fact_ids" if mode == "unapproved-fact" else "body"
            ] = ["not-approved"] if mode == "unapproved-fact" else " \t\n"
            evidence = dict(self.evidence)
            evidence[FIELDS[0]] = "uk-UA"
            calls = []
            with self.subTest(mode=mode):
                with self.assertRaises(LanguageRegistryError) as caught:
                    self.prepare(
                        loaded_registry=loaded, evidence=evidence,
                        save_materials=calls.append,
                    )
                self.assertEqual(
                    caught.exception.code,
                    "UNAPPROVED_FACT" if mode == "unapproved-fact"
                    else "INVALID_TEMPLATE",
                )
                self.assertEqual(calls, [])

    def test_consumer_rejects_blank_noninitial_subject_without_repair(self):
        self.loaded["packs_by_locale"]["uk-UA"]["templates"][
            "question"
        ]["subject"] = " \t"
        self.evidence[FIELDS[0]] = "uk-UA"
        before = copy.deepcopy((self.loaded, self.binding, self.evidence))
        calls = []
        with self.assertRaises(RuleViolation):
            self.prepare(
                required_template_id="question",
                save_materials=calls.append,
            )
        self.assertEqual(calls, [])
        self.assertEqual(
            (self.loaded, self.binding, self.evidence), before
        )

    def test_original_dependency_exception_objects_are_not_wrapped(self):
        # Real F130 is invoked; only one of its dependency boundaries fails.
        for name, error in (
            ("bind_action_locale", ActionLocaleError("sentinel-f120")),
            ("materialize_bound_template",
             TemplateMaterializationError("sentinel-f122")),
            ("validate_materials", RuleViolation("sentinel-consumer")),
        ):
            calls = []
            with self.subTest(dependency=name):
                with mock.patch.object(f130, name, side_effect=error):
                    with self.assertRaises(type(error)) as caught:
                        self.prepare(save_materials=calls.append)
                self.assertIs(caught.exception, error)
                self.assertEqual(calls, [])

    def test_f105_and_f106_exception_identity_from_real_validation(self):
        # Inject only the exception instance, leaving real validators in place.
        binding = copy.deepcopy(self.binding)
        binding["release_mode"] = "OUTBOUND"
        loaded = copy.deepcopy(self.loaded)
        loaded["packs_by_locale"]["uk-UA"]["templates"]["initial"]["body"] = ""
        cases = (
            (f105, "FirstBindingError", FirstBindingError("f105-sentinel"),
             {"binding_config": binding}),
            (f106, "LanguageRegistryError",
             LanguageRegistryError("f106-sentinel"),
             {"loaded_registry": loaded}),
        )
        for module, name, error, arguments in cases:
            calls = []
            with self.subTest(dependency=name):
                with mock.patch.object(
                    module, name, side_effect=lambda code, exc=error: exc
                ):
                    with self.assertRaises(type(error)) as caught:
                        self.prepare(
                            **arguments, save_materials=calls.append
                        )
                self.assertIs(caught.exception, error)
                self.assertEqual(calls, [])

    def test_callback_exception_identity_once_and_next_call_works(self):
        error = RuntimeError("save-sentinel")
        calls = []
        def failing_save(materials):
            calls.append(materials)
            raise error
        before = copy.deepcopy((self.loaded, self.binding, self.evidence))
        with self.assertRaises(RuntimeError) as caught:
            self.prepare(save_materials=failing_save)
        self.assertIs(caught.exception, error)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            (self.loaded, self.binding, self.evidence), before
        )
        result = self.prepare()
        self.assertEqual(result, calls[0])

    def test_selection_deterministic_immutable_and_return_is_detached(self):
        before = copy.deepcopy((self.loaded, self.binding, self.evidence))
        first = self.select()
        self.assertEqual(first, self.select())
        first["locale"] = "changed-by-caller"
        self.assertEqual(self.select()["locale"], "en-GB")
        self.assertEqual(
            (self.loaded, self.binding, self.evidence), before
        )

    def test_selection_uses_no_filesystem_network_clock_or_callback(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("I/O or hidden time during selection")
        with ExitStack() as stack:
            for target in (
                "builtins.open", "io.open", "os.open", "os.listdir",
                "os.scandir", "os.stat", "os.lstat", "os.getenv",
                "socket.socket", "time.time",
            ):
                stack.enter_context(mock.patch(target, side_effect=forbidden))
            for name in ("open", "read_bytes", "read_text", "iterdir",
                         "glob", "rglob"):
                stack.enter_context(
                    mock.patch.object(Path, name, side_effect=forbidden)
                )
            result = self.select()
        self.assertEqual(result["locale"], "en-GB")

    def test_candidate_errors_never_echo_sensitive_input(self):
        marker = "PRIVATE-INPUT-DO-NOT-ECHO"
        evidence = dict(self.evidence, country=marker)
        error = self.assert_candidate_error(
            "INVALID_INPUT", lambda: self.select(evidence=evidence)
        )
        self.assertNotIn(marker, repr(error))
        self.evidence[FIELDS[0]] = marker
        error = self.assert_candidate_error(
            "SELECTED_LOCALE_UNAVAILABLE", self.select
        )
        self.assertNotIn(marker, repr(error))


if __name__ == "__main__":
    unittest.main(verbosity=2)
