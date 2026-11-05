"""判定器校准测试：只测对齐、一致率和混淆矩阵逻辑。"""

from scripts.calibrate_judge import compare_labels, confusion


def test_all_agree():
    result = compare_labels({"a": True, "b": False}, {"a": True, "b": False})

    assert result["compared"] == 2
    assert result["agreement_rate"] == 1.0
    assert result["disagreements"] == []


def test_reports_disagreement():
    result = compare_labels({"q14": False}, {"q14": True})

    assert result["agreement_rate"] == 0.0
    assert result["disagreements"] == [
        {"id": "q14", "human": False, "judge": True}
    ]


def test_skips_failed_judgement():
    """judge 判定失败（None）不能算作不一致，要单独跳过。"""
    result = compare_labels({"a": True, "b": True}, {"a": True, "b": None})

    assert result["compared"] == 1
    assert result["skipped"] == 1
    assert result["agreement_rate"] == 1.0


def test_uses_intersection_only():
    result = compare_labels({"a": True}, {"b": True})

    assert result["compared"] == 0
    assert result["agreement_rate"] is None


def test_confusion_counts_four_cases():
    matrix = confusion(
        {"a": True, "b": True, "c": False, "d": False},
        {"a": True, "b": False, "c": True, "d": False},
    )

    assert matrix["both_faithful"] == 1
    assert matrix["human_ok_judge_reject"] == 1
    assert matrix["human_reject_judge_ok"] == 1
    assert matrix["both_unfaithful"] == 1
