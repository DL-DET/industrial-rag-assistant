# 检索评测

## 运行

```bash
python -m eval.run_eval
```

只调用 Embedding 接口，不调用问答模型，成本低、速度快。

## 评测集

`dataset.jsonl` 共 41 条：

- 30 条有答案，覆盖泵、风机、电机、PLC、安全规范和维修案例
- 11 条无答案，用于后续拒答率评测；其中 u11 是“机械密封安装扭矩”hard negative

字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 题目编号 |
| `question` | 用户问题 |
| `answerable` | 知识库中是否有答案 |
| `category` | 设备/问题类别 |
| `ground_truth` | 参考答案 |
| `gold_sources` | 可接受来源文件与页码 |
| `gold_keywords` | 判定命中所需的关键词 |

## 相关性判定

检索片段满足以下两个条件才算命中：

1. 来源文件属于 `gold_sources`
2. 正文包含 `gold_keywords` 中的**全部**关键词

同一资料同时存在 DOCX 和 PDF，正文等价但页码不同，因此用关键词匹配，避免等价来源被误判。

## 输出

- `report.md`：汇总指标、Top-1 分数分布、逐题结果
- `results.jsonl`：逐题完整检索记录，可继续做 trace 分析
