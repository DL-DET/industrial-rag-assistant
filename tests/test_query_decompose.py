from query_decompose import decompose_question


def test_decompose_cause_and_action():
    parts = decompose_question("WL 污水泵无法启动有哪些原因，如何处理？")

    assert parts == [
        "WL 污水泵无法启动的原因有哪些？",
        "WL 污水泵无法启动的处理方法是什么？",
    ]


def test_decompose_cause_and_action_with_de():
    parts = decompose_question("WL 污水泵泵体漏水的原因和处理方法是什么？")

    assert parts == [
        "WL 污水泵泵体漏水的原因有哪些？",
        "WL 污水泵泵体漏水的处理方法是什么？",
    ]


def test_decompose_two_parameters():
    parts = decompose_question(
        "DTII-800 带式输送机的电机功率和减速机型号是什么？"
    )

    assert parts == [
        "DTII-800 带式输送机的电机功率是多少？",
        "DTII-800 带式输送机的减速机型号是多少？",
    ]


def test_decompose_three_parameters():
    parts = decompose_question(
        "WL 污水泵的额定流量、扬程和配套电机功率范围是多少？"
    )

    assert parts == [
        "WL 污水泵的额定流量是多少？",
        "WL 污水泵的扬程是多少？",
        "WL 污水泵的配套电机功率范围是多少？",
    ]


def test_decompose_single_question_returns_original():
    question = "PLC 控制柜的防护等级是多少？"

    assert decompose_question(question) == [question]


def test_decompose_does_not_split_compound_subject():
    question = "压力容器和旋转类设备在运行状态下禁止做什么？"

    assert decompose_question(question) == [question]
