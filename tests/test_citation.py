"""引用补全测试：只补裸编号，不覆盖模型已经写好的文件名。"""

from langchain_core.documents import Document

from citation import add_citations


def _doc(source, page=None):
    metadata = {"source": source}
    if page is not None:
        metadata["page"] = page
    return Document(page_content="正文", metadata=metadata)


def test_adds_filename_to_bare_citation():
    result = add_citations("根据[资料 1]，带速为 1.6 m/s。", [_doc("手册.pdf")])
    assert result == "根据[资料 1：手册.pdf]，带速为 1.6 m/s。"


def test_keeps_citation_when_filename_follows():
    answer = "[资料 1]《手册.pdf》第 5 页"
    assert add_citations(answer, [_doc("手册.pdf")]) == answer


def test_unknown_number_is_left_alone():
    answer = "见[资料 9]"
    assert add_citations(answer, [_doc("手册.pdf")]) == answer


def test_multiple_citations_map_to_their_own_files():
    result = add_citations("[资料 1] 和 [资料 2]", [_doc("A.pdf"), _doc("B.docx")])
    assert result == "[资料 1：A.pdf] 和 [资料 2：B.docx]"


def test_citation_with_extra_spaces_is_matched():
    result = add_citations("[资料  1]", [_doc("A.pdf")])
    assert result == "[资料 1：A.pdf]"


def test_empty_inputs_are_safe():
    assert add_citations("", [_doc("A.pdf")]) == ""
    assert add_citations("根据[资料 1]", []) == "根据[资料 1]"


def test_answer_without_citation_is_unchanged():
    answer = "知识库中暂无足够依据回答该问题。"
    assert add_citations(answer, [_doc("A.pdf")]) == answer
