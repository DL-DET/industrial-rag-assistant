from eval.answer_metrics import (
    evaluate_answer,
    is_refusal,
    keyword_coverage,
    threshold_table,
)


def test_keyword_coverage_ignores_whitespace():
    assert keyword_coverage("介质温\n度 0~80℃", ["介质温度", "0~80"]) == 1.0


def test_refusal_markers():
    assert is_refusal("知识库中暂无足够依据。")
    assert not is_refusal("介质温度为 0~80℃。")


def test_evaluate_answerable_item():
    item = {
        "answerable": True,
        "gold_keywords": ["500", "轴承润滑油"],
        "gold_sources": [{"file": "手册.pdf", "page": 4}],
    }

    result = evaluate_answer(
        item,
        "运行满 500 小时需要更换轴承润滑油。",
        ["手册.pdf p.4"],
    )

    assert result["coverage"] == 1.0
    assert result["all_keywords"] is True
    assert result["source_hit"] is True
    assert result["refusal"] is False


def test_evaluate_unanswerable_item():
    result = evaluate_answer(
        {"answerable": False, "gold_keywords": [], "gold_sources": []},
        "知识库中暂无足够依据。",
        [],
    )

    assert result["refusal"] is True
    assert result["coverage"] is None


def test_threshold_table_tradeoff():
    records = [
        {"answerable": True, "top_score": 0.8},
        {"answerable": True, "top_score": 0.4},
        {"answerable": False, "top_score": 0.6},
        {"answerable": False, "top_score": 0.3},
    ]

    rows = threshold_table(records, [0.5, 0.7])

    assert rows[0]["answerable_false_refusal_rate"] == 0.5
    assert rows[0]["unanswerable_refusal_rate"] == 0.5
    assert rows[1]["answerable_false_refusal_rate"] == 0.5
    assert rows[1]["unanswerable_refusal_rate"] == 1.0
