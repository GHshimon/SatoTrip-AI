"""
description のNGワードフィルタの回帰テスト（景表法対策）。

検証できない事実断定（受賞・最上級・由来・数値）を含む文だけを落とす。
主観的な雰囲気紹介は残す。
"""
from app.services.spot_import_service import (
    filter_description_ng_words,
    _contains_description_ng_word,
)


def test_removes_award_sentence_keeps_neutral():
    text = "落ち着いた雰囲気の温泉です。ミシュラン三つ星を獲得しています。"
    out = filter_description_ng_words(text)
    assert "落ち着いた雰囲気" in out
    assert "ミシュラン" not in out


def test_removes_superlative_sentence():
    text = "日本一の名湯として知られています。散策が楽しめます。"
    out = filter_description_ng_words(text)
    assert "日本一" not in out
    assert "散策が楽しめます" in out


def test_all_ng_returns_none():
    text = "創業100年の元祖です。年間50万人が来場する日本一の名物です。"
    assert filter_description_ng_words(text) is None


def test_none_and_empty_are_falsy():
    # None はそのまま None、空文字はそのまま空文字（どちらも「中身なし」）
    assert filter_description_ng_words(None) is None
    assert not filter_description_ng_words("")


def test_neutral_text_is_kept():
    text = "海沿いに佇む静かな宿。夕日が美しく眺められます。"
    assert filter_description_ng_words(text) == text


def test_kanshou_is_not_false_positive():
    # 「鑑賞」「観賞」は「賞」を含むが NG ではない（否定先読みで除外）
    assert _contains_description_ng_word("庭園の鑑賞ができます") is False
    assert _contains_description_ng_word("紅葉を観賞できます") is False


def test_award_word_is_detected():
    assert _contains_description_ng_word("グランプリを受賞") is True
