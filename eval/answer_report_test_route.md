# RAG 答案级评测报告

- 生成时间：2026-11-05 18:17:05
- 样本：有答案 32 / 无答案 12
- 拒答路由：开启，阈值 0.75（仅对重排分生效）

## 汇总

| 指标 | 数值 |
| --- | --- |
| 关键词覆盖率 | 1.000 |
| 全部关键词命中率 | 1.000 |
| 来源命中率 | 1.000 |
| 回答引用来源率 | 1.000 |
| 有答案误拒答率 | 0.000 |
| 无答案正确拒答率 | 0.917 |
| 有答案路由拒答率 | 0.000 |
| 无答案路由拒答率 | 0.917 |

## 拒答阈值扫描（仅按 Top-1 分数模拟）

| 阈值 | 有答案误拒答率 | 无答案拒答率 |
| ---: | ---: | ---: |
| 0.3 | 0.000 | 0.167 |
| 0.4 | 0.000 | 0.167 |
| 0.5 | 0.000 | 0.583 |
| 0.6 | 0.000 | 0.833 |
| 0.7 | 0.000 | 0.917 |
| 0.8 | 0.000 | 0.917 |

## 逐题结果

| ID | 类型 | Top-1 分数 | 关键词覆盖 | 全部命中 | 引用来源 | 拒答 |
| --- | --- | ---: | ---: | --- | --- | --- |
| q01 | 有答案 | 1.0 | 1.0 | True | True | False |
| q02 | 有答案 | 0.9999 | 1.0 | True | True | False |
| q04 | 有答案 | 0.9609 | 1.0 | True | True | False |
| q06 | 有答案 | 0.9966 | 1.0 | True | True | False |
| q10 | 有答案 | 1.0 | 1.0 | True | True | False |
| q11 | 有答案 | 0.9982 | 1.0 | True | True | False |
| q13 | 有答案 | 0.9753 | 1.0 | True | True | False |
| q14 | 有答案 | 0.955 | 1.0 | True | True | False |
| q15 | 有答案 | 0.9976 | 1.0 | True | True | False |
| q16 | 有答案 | 0.9719 | 1.0 | True | True | False |
| q21 | 有答案 | 0.9943 | 1.0 | True | True | False |
| q26 | 有答案 | 0.9821 | 1.0 | True | True | False |
| q27 | 有答案 | 0.9975 | 1.0 | True | True | False |
| q29 | 有答案 | 1.0 | 1.0 | True | True | False |
| c01 | 有答案 | 1.0 | 1.0 | True | True | False |
| c02 | 有答案 | 1.0 | 1.0 | True | True | False |
| c04 | 有答案 | 1.0 | 1.0 | True | True | False |
| c06 | 有答案 | 0.9903 | 1.0 | True | True | False |
| c07 | 有答案 | 0.9989 | 1.0 | True | True | False |
| c08 | 有答案 | 1.0 | 1.0 | True | True | False |
| p04 | 有答案 | 0.9998 | 1.0 | True | True | False |
| m04 | 有答案 | 0.9398 | 1.0 | True | True | False |
| m05 | 有答案 | 0.9287 | 1.0 | True | True | False |
| m06 | 有答案 | 0.9708 | 1.0 | True | True | False |
| pl01 | 有答案 | 0.9926 | 1.0 | True | True | False |
| pl02 | 有答案 | 1.0 | 1.0 | True | True | False |
| pl04 | 有答案 | 1.0 | 1.0 | True | True | False |
| s03 | 有答案 | 0.9295 | 1.0 | True | True | False |
| cv01 | 有答案 | 1.0 | 1.0 | True | True | False |
| cv05 | 有答案 | 1.0 | 1.0 | True | True | False |
| cv08 | 有答案 | 0.9994 | 1.0 | True | True | False |
| cv10 | 有答案 | 1.0 | 1.0 | True | True | False |
| u01 | 无答案 | 0.433 | — | None | None | True |
| u02 | 无答案 | 0.4584 | — | None | None | True |
| u04 | 无答案 | 0.6302 | — | None | None | True |
| u08 | 无答案 | 0.1541 | — | None | None | True |
| u09 | 无答案 | 0.8462 | — | None | None | False |
| cu01 | 无答案 | 0.4805 | — | None | None | True |
| u12 | 无答案 | 0.5109 | — | None | None | True |
| u13 | 无答案 | 0.4539 | — | None | None | True |
| u14 | 无答案 | 0.4967 | — | None | None | True |
| u15 | 无答案 | 0.5297 | — | None | None | True |
| u21 | 无答案 | 0.2621 | — | None | None | True |
| u22 | 无答案 | 0.5644 | — | None | None | True |
