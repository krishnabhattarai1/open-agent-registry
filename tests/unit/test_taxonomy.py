"""Unit tests for the capability taxonomy."""

import pytest

from oar.taxonomy import (
    all_codes,
    compute_match_score,
    is_valid_code,
    match_all,
    match_any,
    match_none,
    match_prefix,
    validate_codes,
)


def test_all_codes_returns_list():
    codes = all_codes()
    assert len(codes) > 50
    assert "code.review" in codes
    assert "data.transform" in codes
    assert "text.summarize" in codes


def test_is_valid_code():
    assert is_valid_code("code.review")
    assert is_valid_code("data.transform")
    assert not is_valid_code("fake.capability")
    assert not is_valid_code("code")


def test_validate_codes():
    invalid = validate_codes(["code.review", "bad.code", "text.embed"])
    assert invalid == ["bad.code"]


def test_match_prefix():
    agent = ["code.review", "code.fix", "text.summarize"]
    assert match_prefix("code", agent)
    assert match_prefix("code.review", agent)
    assert not match_prefix("data", agent)


def test_match_all():
    agent = ["code.review", "code.fix", "text.summarize"]
    assert match_all(["code.review", "code.fix"], agent)
    assert match_all(["code"], agent)  # prefix match
    assert not match_all(["code.review", "data.transform"], agent)


def test_match_any():
    agent = ["code.review", "code.fix"]
    assert match_any(["code.review", "data.transform"], agent)
    assert not match_any(["text.summarize", "web.scrape"], agent)


def test_match_none():
    agent = ["code.review", "code.fix"]
    assert match_none(["text.summarize"], agent)
    assert not match_none(["code.review"], agent)
    assert not match_none(["code"], agent)  # prefix match excludes


def test_compute_match_score_full_match():
    score = compute_match_score(["code.review", "code.fix"], None, ["code.review", "code.fix"])
    assert score == 70


def test_compute_match_score_with_want():
    score = compute_match_score(
        ["code.review"],
        ["code.fix"],
        ["code.review", "code.fix"]
    )
    assert score == 100  # 70 + 30


def test_compute_match_score_partial():
    score = compute_match_score(["code.review", "code.gen"], None, ["code.review"])
    assert score == 35  # 1/2 matched * 70
