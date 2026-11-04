# 检索评测

## 运行

```bash
python -m eval.run_eval
```

做 A/B 实验时加标签，避免覆盖基线报告：

```bash
python -m eval.run_eval --label split300
```

测试重排：

```bash
python -m eval.run_eval --rerank
```

默认重排模型是 `qwen3-rerank`；`gte-rerank-v2` 的报告保留为历史对照。

测试 BM25 + 向量混合检索：

```bash
python -m eval.run_eval --hybrid
python -m eval.run_eval --hybrid --rerank
```

测试多部分问题拆解：

```bash
python -m eval.run_eval --decompose
python -m eval.run_eval --decompose --rerank --rerank-top-n 5
```

混合检索和规则拆解目前只用于评测，不接入应用；应用默认仍是“向量召回 + 重排”。
重排实验需要 DashScope 重排额度，免费额度耗尽时会报 `AllocationQuota.FreeTierOnly`。

使用 100 条 v2 评测集：

```bash
python -m eval.run_eval --dataset eval/dataset_v2.jsonl --label v2_vector
python -m eval.run_eval --dataset eval/dataset_v2.jsonl --label v2_rerank --rerank
python -m eval.run_eval --dataset eval/dataset_v2.jsonl --label v2_hybrid --hybrid
python -m eval.run_eval --dataset eval/dataset_v2.jsonl --label v2_hybrid_rerank --hybrid --rerank
```

使用独立评测集：

```bash
python -m eval.run_eval --dataset eval/dataset_dedup.jsonl --label dedup_baseline
python -m eval.run_eval --dataset eval/dataset_dedup.jsonl --label dedup_rerank --rerank
```

只调用 Embedding（以及启用 `--rerank` 时的重排接口），不调用问答模型，成本低、速度快。

## 评测集

`dataset.jsonl` 共 41 条：

- 30 条有答案，覆盖泵、风机、电机、PLC、安全规范和维修案例
- 11 条无答案，用于后续拒答率评测；其中 u11 是“机械密封安装扭矩”hard negative

`dataset_dedup.jsonl` 是同一批题目的去重版本：`gold_sources` 只保留 PDF，
用于验证“去掉重复 DOCX 后指标是否仍然成立”。

`dataset_conveyor.jsonl` 是新增带式输送机 DOCX 的覆盖评测：8 条有答案 +
2 条无答案，用于验证新资料是否可检索、可回答，以及重排对无答案分数的区分度。

`dataset_v2.jsonl` 是扩展后的 100 条评测集：75 条有答案 + 25 条无答案，
覆盖泵、风机、电机、PLC、输送机、安全规范和维修案例。由
`scripts/build_dataset_v2.py` 生成，构建时会校验关键词是否真的出现在对应来源中。

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

匹配前会去掉正文和关键词中的空白字符，避免 PDF 在“介质温度”中间插入换行
导致假阴性。原始语料同时存在 DOCX 和 PDF，正文等价但页码不同，因此用
关键词匹配，避免等价来源被误判。

## 输出

- `report.md`：汇总指标、Top-1 分数分布、逐题结果
- `results.jsonl`：逐题完整检索记录，可继续做 trace 分析
- 带 `--label` 时输出 `report_{label}.md` 和 `results_{label}.jsonl`，基线文件不会被覆盖
