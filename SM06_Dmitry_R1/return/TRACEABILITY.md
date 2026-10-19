# Requirement → code → test → raw log

Normative requirements are in CONTRACT.md (steps 1–6), TASK_ORDER.md and
INTEGRATION.md. Each frozen test reference below is
acceptance/run.py::Acceptance.<test_method>. Every listed CP1 assertion executes
in both pass1_cp1.stderr and pass2_cp1.stderr; stdout is retained alongside.
An own-test inventory follows and supplements these immutable tests.

| Requirement | Implementation | Frozen test / evidence |
|---|---|---|
| Five locales × five kinds, nonempty subject/body, no fact IDs | candidate/packs/*.json | test_pack_shape_all5_kinds_and_no_fact_claim_ids |
| Exact real-chain text, version, one save and input immutability for all 25 cases | prepare_language_materials → actual F130 | test_all25_actual_chain_exact_once_immutable |
| Evidence priority and en-GB default | select_language | test_selection_priority_and_default |
| Unsupported explicit choice fails without trying lower evidence or saving | select_language | test_explicit_unavailable_no_downgrade_zero_save |
| Exact evidence shape, invalid values, mixed/unknown handling | select_language | test_invalid_evidence_country_mixed_unknown_zero_save |
| Registry/binding default and version equality | select_language + real F105/F106 | test_registry_binding_scope_mismatch |
| Drift, missing template, blank body; original errors, zero save | prepare_language_materials → actual F130 | test_drift_missing_blank_zero_save_passthrough |
| Malformed loaded registry produces F106 error, not raw KeyError | select_language + real F106 | test_malformed_registry_no_raw_keyerror |
| Unapproved facts, blank subject and naive now cannot save | actual F105/F106/F130 | test_unapproved_fact_blank_subject_invalid_now_zero_save |
| Dependency exception object identity and zero save | prepare_language_materials → actual F130 | test_dependency_exception_identity |
| Missing permitted English default fails closed | select_language + real F105 | test_unavailable_english_default_rejects |
| Callback exception object identity, one attempt, no retry | prepare_language_materials → actual F130 | test_callback_exception_identity_and_no_retry |
| Extra synthetic locale works without an enum change | select_language | test_synthetic_extra_locale_no_hardcoded_enum |
| Existing dependencies unchanged and compatible | reference/ with frozen CP0 | pass1_cp0.stderr / pass2_cp0.stderr: required six suites / 152 tests |
| Protected bytes preserved before/after tests | PACKAGE_CHECK.py and issued-ZIP comparison | pass{1,2}_package_{before,after}.stdout |
| Nonempty own tests and no skipped suites | verify_sm06.py result parsing | commands.json; RESULT.json |
| Complete ZIP, exact paths, SHA-256 coverage, reproducibility | verify_sm06.py | SHA256SUMS.json; external SM06_RETURN_R1.validation.json |
| Equivalent neutral sample intent in five languages | candidate/packs/*.json | SEMANTIC_REVIEW.md: internal self-review; independent language QA NOT_RUN |
| Trusted producers, installation, restore and full runtime | Separate integration-owner acceptance | NOT_RUN; see INTEGRATION.md |

All raw files named above are in return/evidence/verification/.
A PASS requires every executed command and mandatory count/no-skip check to pass;
the table describes required coverage, while RESULT.json records actual results.

## Submitted candidate tests

- candidate/tests/test_sm06.py::CandidateLanguageTests.test_all_25_materials_exact_text_versions_callback_identity
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_all_evidence_fields_validated_before_priority_or_binding
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_all_priority_combinations_and_exact_result_shape
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_callback_exception_identity_once_and_next_call_works
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_candidate_errors_never_echo_sensitive_input
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_consumer_rejects_blank_noninitial_subject_without_repair
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_exact_evidence_fieldset_forbids_country_and_raw_text
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_f105_and_f106_exception_identity_from_real_validation
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_f106_full_tree_validation_precedes_scope_and_selection
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_first_binding_error_precedes_registry_scope_and_selection
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_invalid_template_and_pin_ids_are_original_f120_errors
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_locale_id_boundaries_case_and_unknown_are_not_normalized
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_malformed_loaded_containers_use_f106_not_raw_key_errors
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_missing_default_is_rejected_and_never_silently_replaced
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_missing_template_is_not_replaced_and_never_saved
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_naive_invalid_and_expired_now_use_real_first_binding
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_non_dict_root_arguments_fail_before_dependency_checks
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_original_dependency_exception_objects_are_not_wrapped
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_pack_contract_five_kinds_versions_and_no_claim_ids
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_public_signatures_and_error_contract
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_scope_checks_versions_defaults_and_product_english
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_selected_pack_pin_not_unselected_preference_pin
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_selection_deterministic_immutable_and_return_is_detached
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_selection_uses_no_filesystem_network_clock_or_callback
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_synthetic_locale_works_through_real_materialization
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_unapproved_fact_and_blank_body_fail_before_save
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_unsupported_higher_priority_does_not_downgrade_or_save
- candidate/tests/test_sm06.py::CandidateLanguageTests.test_whitespace_unicode_and_template_literals_remain_exact
