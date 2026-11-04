"""构建 100 条评测集 v2。

规则：
- 在 v1 的 41 条去重题 + 10 条输送机题基础上，新增 37 条有答案、12 条无答案。
- 每条有答案题的关键词必须能在对应来源中找到，否则构建失败。
- 输出 eval/dataset_v2.jsonl，不覆盖 v1。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

PDF_NAME = "工业设备RAG知识库文本资料汇编.pdf"
DOCX_NAME = "工业设备RAG知识库补充资料_带式输送机.docx"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = PROJECT_ROOT / "data" / PDF_NAME
DOCX_PATH = PROJECT_ROOT / "data" / DOCX_NAME
OUTPUT_PATH = PROJECT_ROOT / "eval" / "dataset_v2.jsonl"

_WHITESPACE = re.compile(r"\s+")


def normalize(text: str) -> str:
    return _WHITESPACE.sub("", text)


def load_v1() -> list[dict]:
    items: list[dict] = []
    for name in ["dataset_dedup.jsonl", "dataset_conveyor.jsonl"]:
        path = PROJECT_ROOT / "eval" / name
        items.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return items


def pdf_item(
    item_id: str,
    question: str,
    category: str,
    ground_truth: str,
    page: int,
    keywords: list[str],
) -> dict:
    return {
        "id": item_id,
        "question": question,
        "answerable": True,
        "category": category,
        "ground_truth": ground_truth,
        "gold_sources": [{"file": PDF_NAME, "page": page}],
        "gold_keywords": keywords,
    }


def docx_item(
    item_id: str,
    question: str,
    category: str,
    ground_truth: str,
    keywords: list[str],
) -> dict:
    return {
        "id": item_id,
        "question": question,
        "answerable": True,
        "category": category,
        "ground_truth": ground_truth,
        "gold_sources": [{"file": DOCX_NAME, "page": None}],
        "gold_keywords": keywords,
    }


def unanswerable(item_id: str, question: str, category: str) -> dict:
    return {
        "id": item_id,
        "question": question,
        "answerable": False,
        "category": category,
        "ground_truth": "",
        "gold_sources": [],
        "gold_keywords": [],
    }


NEW_ITEMS = [
    # 泵：5 条
    pdf_item(
        "p01",
        "WL 污水泵安装时，泵体和电机电缆有哪些要求？",
        "泵/安装",
        "泵体垂直固定，底座地脚螺栓对角锁紧；电机电缆做防水密封，外壳可靠接地。",
        3,
        ["垂直固定", "地脚螺栓", "防水密封"],
    ),
    pdf_item(
        "p02",
        "WL 污水泵每班巡检需要观察哪些内容？",
        "泵/巡检",
        "观察出口压力、异响、振动和机械密封滴水情况；泵体外壳温度不超过 75℃；检查底座有无松动。",
        4,
        ["出口压力", "机械密封", "75℃"],
    ),
    pdf_item(
        "p03",
        "WL 污水泵的定期维护包括哪些项目？",
        "泵/维护",
        "运行满 500 小时更换轴承润滑油；每季度检查机械密封磨损；每半年清理叶轮和泵壳内部杂物。",
        4,
        ["500", "机械密封磨损", "每半年"],
    ),
    pdf_item(
        "p04",
        "WL 污水泵泵体振动剧烈、异响大的原因和处理方法是什么？",
        "泵/故障",
        "原因包括地脚螺栓松动、轴承损坏、叶轮不平衡；处理包括紧固地脚、更换轴承、做叶轮动平衡。",
        4,
        ["地脚螺栓", "轴承损坏", "叶轮不平衡"],
    ),
    pdf_item(
        "p05",
        "WL 污水泵的泵体外壳温度上限是多少？",
        "泵/参数",
        "泵体外壳温度不超过 75℃。",
        4,
        ["泵体外壳", "75℃"],
    ),
    # 风机：5 条
    pdf_item(
        "f01",
        "4-72 风机每月需要做哪些保养？",
        "风机/维护",
        "每月加注轴承润滑脂，并检查地脚螺栓。",
        5,
        ["润滑脂", "地脚螺栓"],
    ),
    pdf_item(
        "f02",
        "4-72 风机每周需要检查什么？",
        "风机/巡检",
        "每周清理进风口滤网灰尘，检查皮带磨损。",
        5,
        ["滤网", "皮带磨损"],
    ),
    pdf_item(
        "f03",
        "4-72 风机风量不足的原因和处理方法是什么？",
        "风机/故障",
        "原因包括入口滤网堵塞、叶轮磨损、管路漏风；处理包括清洗滤网、修补漏风点、检测叶轮磨损。",
        5,
        ["滤网堵塞", "叶轮磨损", "管路漏风"],
    ),
    pdf_item(
        "f04",
        "4-72 风机巡检时如何判断轴承异常？",
        "风机/巡检",
        "轴承温度不超过 70℃，观察振动值，并监听轴承有无杂音。",
        5,
        ["杂音", "70℃", "振动值"],
    ),
    pdf_item(
        "f05",
        "4-72 风机运转时禁止靠近哪些部位？",
        "风机/安全",
        "风机运转时禁止靠近叶轮和皮带传动部位。",
        4,
        ["叶轮", "皮带传动"],
    ),
    # 电机：6 条
    pdf_item(
        "m01",
        "变频电机的冷却方式和防护等级是什么？",
        "电机/参数",
        "防护等级 IP54，冷却方式为自扇冷。",
        5,
        ["自扇冷", "IP54"],
    ),
    pdf_item(
        "m02",
        "变频电机运行时三相电流不平衡度上限是多少？",
        "电机/巡检",
        "三相电流不平衡度不大于 10%。",
        6,
        ["10%", "三相电流"],
    ),
    pdf_item(
        "m03",
        "变频电机巡检时对接线盒有什么要求？",
        "电机/巡检",
        "接线盒无发热、焦味。",
        6,
        ["接线盒", "发热", "焦味"],
    ),
    pdf_item(
        "m04",
        "变频电机的定期维护有哪些要求？",
        "电机/维护",
        "每季度紧固接线端子；每年检测绝缘电阻；轴承每 2000 运行小时补充润滑脂。",
        6,
        ["每季度", "每年", "2000"],
    ),
    pdf_item(
        "m05",
        "变频电机出现异响的原因有哪些？",
        "电机/故障",
        "常见原因包括轴承损坏、转子扫膛、紧固件松动。",
        6,
        ["轴承损坏", "转子扫膛", "紧固件松动"],
    ),
    pdf_item(
        "m06",
        "变频器报过流时应该怎么排查？",
        "电机/故障",
        "先检查负载卡滞、电缆绝缘破损和变频器参数；必要时脱开电机做空载测试，判断机械还是电气故障。",
        6,
        ["负载卡滞", "电缆绝缘破损", "空载测试"],
    ),
    # PLC：5 条
    pdf_item(
        "pl01",
        "PLC 控制柜内通常包含哪些模块和器件？",
        "PLC/环境",
        "包含 CPU 模块、DI/DO 数字量模块、AI/AO 模拟量模块、24V 直流电源和继电器端子。",
        6,
        ["CPU", "DI/DO", "24V"],
    ),
    pdf_item(
        "pl02",
        "PLC 控制柜的运行环境有哪些要求？",
        "PLC/环境",
        "柜内环境温度 0~45℃，防尘，避免水汽和腐蚀性气体。",
        6,
        ["0~45", "防尘", "水汽"],
    ),
    pdf_item(
        "pl03",
        "PLC 控制柜每月维护需要做什么？",
        "PLC/维护",
        "每月清理柜内灰尘，清理时必须断电吹扫。",
        6,
        ["断电吹扫", "灰尘"],
    ),
    pdf_item(
        "pl04",
        "PLC 控制柜 CPU 红灯故障的原因和处理方法是什么？",
        "PLC/故障",
        "原因包括程序错误、存储卡损坏、模块硬件故障；处理包括查看诊断缓冲区、重新下载程序、检查存储卡。",
        7,
        ["程序错误", "存储卡损坏", "诊断缓冲区"],
    ),
    pdf_item(
        "pl05",
        "PLC 数字量输入信号无反馈时怎么处理？",
        "PLC/故障",
        "检查传感器供电、线路断线和端子虚接，用万用表测量 24V 信号。",
        7,
        ["传感器供电", "线路断线", "24V"],
    ),
    # 安全与案例：3 条
    pdf_item(
        "s01",
        "压力容器和旋转类设备在运行状态下禁止做什么？",
        "安全规范",
        "禁止在运行状态下拆卸密封和盖板。",
        7,
        ["拆卸密封", "盖板"],
    ),
    pdf_item(
        "s02",
        "设备试运行前需要确认什么？",
        "安全规范",
        "确认所有防护装置和防护罩安装到位。",
        7,
        ["防护装置", "防护罩"],
    ),
    pdf_item(
        "s03",
        "历史案例2之后增加了什么维护要求？",
        "维修案例",
        "案例2处理后增加了滤网每周清理要求。",
        7,
        ["滤网", "每周清理"],
    ),
    # 输送机：13 条
    docx_item(
        "cv01",
        "DTII-800 带式输送机的输送长度、提升高度和最大倾角是多少？",
        "输送机/参数",
        "输送长度 120 m，提升高度不大于 25 m，最大倾角 18°。",
        ["120 m", "25 m", "18°"],
    ),
    docx_item(
        "cv02",
        "DTII-800 使用什么规格的胶带？",
        "输送机/参数",
        "胶带型号 EP200，4 层，上胶 4.5 mm，下胶 1.5 mm。",
        ["EP200", "4 层"],
    ),
    docx_item(
        "cv03",
        "DTII-800 的托辊直径和承载段、回程段间距是多少？",
        "输送机/参数",
        "托辊直径 φ89×305 mm，承载段间距 1.2 m，回程段间距 3.0 m。",
        ["φ89×305", "1.2 m", "3.0 m"],
    ),
    docx_item(
        "cv04",
        "DTII-800 采用什么张紧方式，总行程是多少？",
        "输送机/参数",
        "采用螺旋张紧，总行程 500 mm。",
        ["螺旋张紧", "500 mm"],
    ),
    docx_item(
        "cv05",
        "带式输送机基础混凝土强度和地脚螺栓位置偏差有什么要求？",
        "输送机/安装",
        "基础混凝土强度不低于 C20，地脚螺栓预留孔位置偏差不大于 5 mm。",
        ["C20", "5 mm"],
    ),
    docx_item(
        "cv06",
        "带式输送机机架中心线直线度要求是多少？",
        "输送机/安装",
        "机架中心线直线度不大于 3 mm/10 m，全长不大于 10 mm。",
        ["3 mm/10 m", "10 mm"],
    ),
    docx_item(
        "cv07",
        "带式输送机胶带接头强度和中心线偏差有什么要求？",
        "输送机/安装",
        "接头强度不低于胶带本体强度的 80%，接头中心线与胶带中心线偏差不大于 5 mm。",
        ["80%", "5 mm"],
    ),
    docx_item(
        "cv08",
        "带式输送机安装时张紧装置需要保留多少行程？",
        "输送机/安装",
        "安装时应保留至少 1/2 行程。",
        ["1/2 行程"],
    ),
    docx_item(
        "cv09",
        "带式输送机需要安装哪些安全保护装置？",
        "输送机/安全",
        "需要安装防护罩、急停拉绳、跑偏开关、打滑开关和料流检测装置。",
        ["急停拉绳", "跑偏开关", "打滑开关"],
    ),
    docx_item(
        "cv10",
        "带式输送机空载调试的时间和电流要求是什么？",
        "输送机/调试",
        "空载调试不少于 2 小时，空载电流不大于电机额定电流的 60%。",
        ["2 小时", "60%"],
    ),
    docx_item(
        "cv11",
        "带式输送机负载调试如何分级加载？",
        "输送机/调试",
        "按 25%、50%、75%、100% 分级加载，每级运行不少于 30 分钟。",
        ["25%", "50%", "100%"],
    ),
    docx_item(
        "cv15",
        "带式输送机滚筒轴承首次补脂和后续补脂周期是多少？",
        "输送机/维护",
        "首次运行 200 小时后补脂，之后每 1000 小时补充一次。",
        ["200 小时", "1000 小时"],
    ),
    docx_item(
        "cv21",
        "带式输送机胶带撕裂的原因和处理方法是什么？",
        "输送机/故障",
        "原因包括尖锐物料卡入、托辊缺失、清扫器损坏；处理包括停机清除异物、修补或更换胶带、补齐托辊。",
        ["尖锐物料", "托辊缺失", "更换胶带"],
    ),
    # 无答案：12 条
    unanswerable("u12", "WL 污水泵的电机品牌是什么？", "无答案/型号"),
    unanswerable("u13", "4-72 风机的叶轮材质是什么？", "无答案/型号"),
    unanswerable("u14", "4-72 风机的配套电机功率是多少？", "无答案/参数"),
    unanswerable("u15", "变频电机的绝缘等级是多少？", "无答案/参数"),
    unanswerable("u16", "变频电机允许的最高环境湿度是多少？", "无答案/参数"),
    unanswerable("u17", "PLC 控制柜的备用电源续航时间是多少？", "无答案/参数"),
    unanswerable("u18", "PLC S7-1200 的固件版本是多少？", "无答案/型号"),
    unanswerable("u19", "DTII-800 带式输送机胶带的生产厂家是什么？", "无答案/型号"),
    unanswerable("u20", "DTII-800 带式输送机托辊的使用寿命是多少小时？", "无答案/参数"),
    unanswerable("u21", "带式输送机机架使用的钢材牌号是什么？", "无答案/型号"),
    unanswerable("u22", "带式输送机胶带接头的硫化压力是多少？", "无答案/参数"),
    unanswerable("u23", "DTII-800 带式输送机的年维护成本是多少？", "无答案/管理"),
]


def build_pdf_pages() -> dict[int, str]:
    reader = PdfReader(PDF_PATH)
    return {
        index: normalize(page.extract_text() or "")
        for index, page in enumerate(reader.pages, start=1)
    }


def build_docx_text() -> str:
    document = Document(DOCX_PATH)
    parts = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    return normalize("\n".join(parts))


def validate(items: list[dict], pdf_pages: dict[int, str], docx_text: str) -> None:
    ids = set()
    questions = set()
    for item in items:
        if item["id"] in ids:
            raise SystemExit(f"重复 ID：{item['id']}")
        ids.add(item["id"])

        normalized_question = normalize(item["question"])
        if normalized_question in questions:
            raise SystemExit(f"重复问题：{item['id']} {item['question']}")
        questions.add(normalized_question)

        if not item["answerable"]:
            if item["gold_sources"] or item["gold_keywords"]:
                raise SystemExit(f"无答案题不应有 gold：{item['id']}")
            continue

        if not item["gold_sources"] or not item["gold_keywords"]:
            raise SystemExit(f"有答案题缺少 gold：{item['id']}")

        for source in item["gold_sources"]:
            if source["file"] == PDF_NAME:
                text = pdf_pages[source["page"]]
            elif source["file"] == DOCX_NAME:
                text = docx_text
            else:
                raise SystemExit(f"未知来源：{source['file']}")

            missing = [
                keyword
                for keyword in item["gold_keywords"]
                if normalize(keyword) not in text
            ]
            if missing:
                raise SystemExit(
                    f"{item['id']} 在 {source['file']} p.{source['page']} 缺少关键词：{missing}"
                )


def main() -> None:
    items = load_v1() + NEW_ITEMS
    pdf_pages = build_pdf_pages()
    docx_text = build_docx_text()
    validate(items, pdf_pages, docx_text)

    OUTPUT_PATH.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in items) + "\n",
        encoding="utf-8",
    )
    answerable = sum(1 for item in items if item["answerable"])
    print(f"total={len(items)} answerable={answerable} unanswerable={len(items) - answerable}")
    print(f"output={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
