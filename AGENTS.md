# AGENTS

## TDD suitability review

This project is **good enough to work with TDD, but not yet strongly optimized for it**.

Current strengths:

- The public API is small and easy to drive from tests (`Config`, `load_config`, decode helpers).
- The package is mostly deterministic and side effects are isolated to file and environment loading.
- Existing tests exercise behavior from the outside instead of overfitting to internals.
- Error types are explicit, which is useful for red-first test writing.

Current gaps:

- Most tests are concentrated in a single file, so scenarios are not grouped by feature or failure mode.
- There are not enough focused failure-path tests for parser and decoder edge cases.
- There is no guardrail for test naming, test layout, or red-green-refactor workflow.
- There is no lightweight command for running a narrow subset while developing one behavior.
- Some important compatibility rules are only implicitly covered by broad tests.

## Recommended improvements

1. Split tests by behavior area.
   - `tests/test_merge_precedence.py`
   - `tests/test_file_loading.py`
   - `tests/test_dotenv_loading.py`
   - `tests/test_decode.py`
   - `tests/test_public_api.py`

2. Prefer one behavior per test.
   - Keep each test focused on one rule and one failure reason.
   - Avoid mixing precedence, parsing, and decoding assertions in a single case unless the interaction itself is the feature.

3. Expand regression coverage for edge cases.
   - Missing file vs unsupported extension
   - Non-mapping top-level config payloads
   - Empty YAML file behavior
   - Key normalization with mixed case and hyphen/underscore inputs
   - Source ordering when same-priority sources are loaded multiple times
   - `decode()` for list, tuple, dict, union, optional, and nested container failures
   - Bool coercion failures and int/bool ambiguity
   - `.env` quoting, comments, `export` syntax, duplicate keys, and invalid assignments

4. Keep tests public-API first.
   - Prefer testing through `Config` and `load_config`.
   - Only add lower-level unit tests for helpers when a bug cannot be expressed clearly through the public API.

5. Use regression tests for every bug fix.
   - Write the failing test first.
   - Confirm it fails for the intended reason.
   - Implement the minimal production change.
   - Refactor only after the test passes.

## Development guide

### Core TDD workflow

1. Add or update a failing test for the behavior.
2. Run the narrowest possible pytest target.
3. Implement the smallest change that makes the test pass.
4. Refactor production or test code without changing behavior.
5. Run the relevant focused tests again.
6. Before finishing, run the full test suite.

### Test organization rules

- Put new tests near the behavior they cover instead of extending one catch-all test file indefinitely.
- Name tests by observable behavior, for example:
  - `test_load_env_ignores_unprefixed_keys`
  - `test_decode_union_reports_all_candidate_failures`
  - `test_load_file_rejects_non_mapping_top_level_json`
- Prefer fixtures like `tmp_path` and explicit inline data over shared mutable helpers.
- Keep assertions specific enough to explain the regression.

### Coverage priorities for future work

When changing merge behavior:

- Add precedence tests first.
- Add ordering tests when two sources share a priority class.
- Verify normalized keys do not change merge expectations.

When changing file parsing:

- Add one success case and one failure case per format.
- Assert the exact package error type raised.

When changing dotenv behavior:

- Cover prefix filtering, nested delimiter mapping, quoting, comments, blank values, and invalid lines.

When changing decode behavior:

- Cover both successful coercion and failure messages.
- Add nested path assertions so errors remain debuggable.

### Suggested pytest commands

Run one file:

```bash
uv run --group dev pytest tests/test_public_api.py
```

Run one test:

```bash
uv run --group dev pytest tests/test_decode.py -k literal
```

Run the full suite:

```bash
uv run --group dev pytest
```

## Suggested next test additions

- Add tests for `Enum` decode support if that API is introduced.
- Add tests for `Path` decoding if path-like targets are supported.
- Add tests for richer source provenance on nested merged objects.
- Add tests for invalid JSON, invalid TOML, and invalid YAML decoding errors with stable message assertions.
