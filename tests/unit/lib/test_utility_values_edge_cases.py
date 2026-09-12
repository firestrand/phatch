from __future__ import annotations

import codecs
import importlib.util
import locale
import sys

import pytest

from phatch.lib import unicoding


def test_unicoding_module_falls_back_from_unknown_locale_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a locale reporting an unknown encoding and a valid preference
    original_lookup = codecs.lookup
    monkeypatch.setattr(locale, "getencoding", lambda: "unknown-test-encoding")
    monkeypatch.setattr(locale, "getpreferredencoding", lambda: "utf-8")

    def lookup(encoding: str):
        if encoding == "unknown-test-encoding":
            raise LookupError(encoding)
        return original_lookup(encoding)

    monkeypatch.setattr(codecs, "lookup", lookup)
    module_name = "phatch.lib._unicoding_encoding_test"
    spec = importlib.util.spec_from_file_location(module_name, unicoding.__file__)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    # When: the module initializes its display encoding
    spec.loader.exec_module(module)

    # Then: the valid preferred encoding replaces the unknown locale value
    assert module.ENCODING == "utf-8"


def test_fix_filename_returns_none_after_failed_byte_decodings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: invalid bytes and no matching filesystem entry
    monkeypatch.setattr(unicoding.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(unicoding.system, "is_file", lambda path: False)

    # When: recovery exhausts its candidate encodings
    recovered = unicoding.fix_filename(b"\xff", encoding="utf-8")

    # Then: the absent filename is represented by None
    assert recovered is None


def test_fix_filename_skips_unencodable_text_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: text outside Latin-1 and a deterministic missing filesystem
    monkeypatch.setattr(unicoding.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(unicoding.system, "is_file", lambda path: False)
    monkeypatch.setattr(unicoding, "ENCODING", "ascii")

    # When: recovery tries each candidate encoding
    recovered = unicoding.fix_filename("東京.txt", encoding="latin1")

    # Then: encoding failures are skipped and no false match is produced
    assert recovered is None


def test_fix_filename_finds_alternatively_decoded_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: mojibake text whose filesystem-decoded bytes identify a file
    mojibake = "cafÃ©.txt"
    monkeypatch.setattr(unicoding.system, "is_file", lambda path: False)
    monkeypatch.setattr(
        unicoding.os.path, "isfile", lambda path: path == "café.txt"
    )

    # When: Latin-1 re-encoding is attempted first
    recovered = unicoding.fix_filename(mojibake, encoding="latin1")

    # Then: the readable filename is recovered
    assert recovered == "café.txt"
