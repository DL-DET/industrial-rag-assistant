from eval.answer_metrics import (
    evaluate_answer,
    is_refusal,
    keyword_coverage,
    threshold_table,
)


def test_keyword_coverage_ignores_whitespace():
    assert keyword_coverage("介质温\n度 0~80℃", ["介质温度", "0~80"]) == 1.0


def test_keyword_coverage_allows_filler_between_chars():
    """“叶轮腐蚀”要能匹配“叶轮是否有腐蚀”，不能因为虚词判成漏答。"""
    assert keyword_coverage("拆机检查叶轮是否有腐蚀现象", ["叶轮腐蚀"]) == 1.0


def test_keyword_coverage_normalizes_units():
    """“5 mm”和“5毫米”是同一条要求，单位写法不能造成假阴性。"""
    assert keyword_coverage("位置偏差不超过5毫米", ["5 mm"]) == 1.0


def test_keyword_coverage_allows_filler_inside_compound():
    assert keyword_coverage("张紧装置应保留至少1/2的行程", ["1/2 行程"]) == 1.0


def test_keyword_coverage_still_rejects_missing_keyword():
    """放宽匹配不能变成万能匹配：没提到就该判 0。"""
    assert keyword_coverage("基础混凝土强度不低于C20。", ["5 mm"]) == 0.0


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
