"""忠实度判定测试：只测解析和降级，不真正调用模型。"""

from langchain_core.documents import Document
from langchain_core.messages import AIMessage

from eval.faithfulness import judge_faithfulness, parse_judgement


def _doc(source="手册.pdf"):
    return Document(
        page_content="轴承温度不高于 70 摄氏度。",
        metadata={"source": source},
    )


class FakeModel:
    def __init__(self, content):
        self.content = content
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return AIMessage(content=self.content)


def test_parse_plain_json():
    result = parse_judgement(
        '{"supported": true, "unsupported_claims": [], "reason": "一致"}'
    )
    assert result.supported is True
    assert result.reason == "一致"


def test_parse_json_in_code_fence():
    text = (
        "```json\n"
        '{"supported": false, "unsupported_claims": ["第 2 条"], "reason": "方向相反"}\n'
        "```"
    )
    result = parse_judgement(text)
    assert result.supported is False
    assert result.unsupported_claims == ["第 2 条"]


def test_parse_rejects_garbage():
    assert parse_judgement("我觉得没问题") is None


def test_parse_rejects_missing_field():
    assert parse_judgement('{"reason": "缺字段"}') is None


def test_judge_skips_refusal():
    model = FakeModel('{"supported": false}')
    result = judge_faithfulness(
        "问题",
        "知识库中暂无足够依据回答该问题。",
        [_doc()],
        model=model,
    )
    assert result.supported is True
    assert result.reason == "拒答，无结论可判定"
    assert model.calls == 0


def test_judge_returns_unsupported_claims():
    model = FakeModel(
        '{"supported": false, "unsupported_claims": ["温度上限说反了"], '
        '"reason": "方向相反"}'
    )
    result = judge_faithfulness(
        "轴承温度上限？",
        "轴承温度应高于 70℃。",
        [_doc()],
        model=model,
    )
    assert result.supported is False
    assert result.unsupported_claims == ["温度上限说反了"]
    assert model.calls == 1


def test_judge_degrades_when_output_unparsable():
    model = FakeModel("我看不出来")
    result = judge_faithfulness("问题", "答案内容。", [_doc()], model=model)
    assert result.supported is None
    assert result.reason == "判定输出无法解析"
