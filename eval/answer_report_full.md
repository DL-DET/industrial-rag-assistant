# RAG 答案级评测报告

- 生成时间：2026-11-04 17:08:51
- 样本：有答案 75 / 无答案 25

## 汇总

| 指标 | 数值 |
| --- | --- |
| 关键词覆盖率 | 0.962 |
| 全部关键词命中率 | 0.920 |
| 来源命中率 | 1.000 |
| 回答引用来源率 | 0.853 |
| 有答案误拒答率 | 0.000 |
| 无答案正确拒答率 | 0.800 |

## 拒答阈值扫描（仅按 Top-1 分数模拟）

| 阈值 | 有答案误拒答率 | 无答案拒答率 |
| ---: | ---: | ---: |
| 0.3 | 0.000 | 0.240 |
| 0.4 | 0.000 | 0.320 |
| 0.5 | 0.000 | 0.560 |
| 0.6 | 0.000 | 0.760 |
| 0.7 | 0.000 | 0.960 |
| 0.8 | 0.000 | 0.960 |

## 逐题结果

| ID | 类型 | Top-1 分数 | 关键词覆盖 | 全部命中 | 引用来源 | 拒答 |
| --- | --- | ---: | ---: | --- | --- | --- |
| q01 | 有答案 | 1.0 | 1.0 | True | True | False |
| q02 | 有答案 | 0.9999 | 1.0 | True | True | False |
| q03 | 有答案 | 1.0 | 1.0 | True | True | False |
| q04 | 有答案 | 0.9609 | 1.0 | True | True | False |
| q05 | 有答案 | 0.994 | 1.0 | True | True | False |
| q06 | 有答案 | 0.9966 | 1.0 | True | True | False |
| q07 | 有答案 | 0.9434 | 1.0 | True | True | False |
| q08 | 有答案 | 0.9368 | 1.0 | True | True | False |
| q09 | 有答案 | 0.9361 | 1.0 | True | True | False |
| q10 | 有答案 | 1.0 | 1.0 | True | True | False |
| q11 | 有答案 | 0.9982 | 1.0 | True | True | False |
| q12 | 有答案 | 0.9986 | 0.6666666666666666 | False | True | False |
| q13 | 有答案 | 0.9753 | 1.0 | True | True | False |
| q14 | 有答案 | 0.955 | 0.6666666666666666 | False | True | False |
| q15 | 有答案 | 0.9976 | 1.0 | True | True | False |
| q16 | 有答案 | 0.9719 | 1.0 | True | True | False |
| q17 | 有答案 | 0.9996 | 1.0 | True | True | False |
| q18 | 有答案 | 0.9881 | 1.0 | True | True | False |
| q19 | 有答案 | 0.977 | 1.0 | True | True | False |
| q20 | 有答案 | 0.9926 | 1.0 | True | True | False |
| q21 | 有答案 | 0.9943 | 1.0 | True | True | False |
| q22 | 有答案 | 1.0 | 1.0 | True | True | False |
| q23 | 有答案 | 1.0 | 1.0 | True | True | False |
| q24 | 有答案 | 1.0 | 1.0 | True | False | False |
| q25 | 有答案 | 0.9863 | 1.0 | True | True | False |
| q26 | 有答案 | 0.9821 | 1.0 | True | True | False |
| q27 | 有答案 | 0.9975 | 1.0 | True | True | False |
| q28 | 有答案 | 0.9864 | 1.0 | True | True | False |
| q29 | 有答案 | 1.0 | 1.0 | True | True | False |
| q30 | 有答案 | 0.9884 | 1.0 | True | True | False |
| c01 | 有答案 | 1.0 | 1.0 | True | False | False |
| c02 | 有答案 | 1.0 | 1.0 | True | True | False |
| c03 | 有答案 | 1.0 | 1.0 | True | False | False |
| c04 | 有答案 | 1.0 | 1.0 | True | False | False |
| c05 | 有答案 | 0.9996 | 1.0 | True | True | False |
| c06 | 有答案 | 0.9903 | 1.0 | True | True | False |
| c07 | 有答案 | 0.9989 | 1.0 | True | True | False |
| c08 | 有答案 | 1.0 | 1.0 | True | True | False |
| p01 | 有答案 | 1.0 | 1.0 | True | True | False |
| p02 | 有答案 | 0.9792 | 1.0 | True | True | False |
| p03 | 有答案 | 0.9358 | 1.0 | True | True | False |
| p04 | 有答案 | 0.9998 | 1.0 | True | True | False |
| p05 | 有答案 | 0.9571 | 1.0 | True | True | False |
| f01 | 有答案 | 0.9442 | 1.0 | True | True | False |
| f02 | 有答案 | 0.9626 | 1.0 | True | True | False |
| f03 | 有答案 | 0.96 | 1.0 | True | True | False |
| f04 | 有答案 | 0.9478 | 0.6666666666666666 | False | True | False |
| f05 | 有答案 | 0.9914 | 1.0 | True | False | False |
| m01 | 有答案 | 0.9925 | 1.0 | True | True | False |
| m02 | 有答案 | 0.9557 | 1.0 | True | True | False |
| m03 | 有答案 | 0.9613 | 1.0 | True | True | False |
| m04 | 有答案 | 0.9398 | 1.0 | True | True | False |
| m05 | 有答案 | 0.9287 | 1.0 | True | True | False |
| m06 | 有答案 | 0.9708 | 1.0 | True | True | False |
| pl01 | 有答案 | 0.9926 | 1.0 | True | True | False |
| pl02 | 有答案 | 1.0 | 1.0 | True | True | False |
| pl03 | 有答案 | 0.9955 | 1.0 | True | False | False |
| pl04 | 有答案 | 1.0 | 1.0 | True | True | False |
| pl05 | 有答案 | 0.9901 | 1.0 | True | False | False |
| s01 | 有答案 | 0.9977 | 1.0 | True | True | False |
| s02 | 有答案 | 0.9722 | 1.0 | True | True | False |
| s03 | 有答案 | 0.9295 | 1.0 | True | True | False |
| cv01 | 有答案 | 1.0 | 1.0 | True | False | False |
| cv02 | 有答案 | 1.0 | 1.0 | True | True | False |
| cv03 | 有答案 | 0.9987 | 0.6666666666666666 | False | False | False |
| cv04 | 有答案 | 0.8134 | 1.0 | True | True | False |
| cv05 | 有答案 | 1.0 | 0.5 | False | False | False |
| cv06 | 有答案 | 0.9994 | 1.0 | True | True | False |
| cv07 | 有答案 | 1.0 | 1.0 | True | True | False |
| cv08 | 有答案 | 0.9994 | 0.0 | False | True | False |
| cv09 | 有答案 | 0.9695 | 1.0 | True | False | False |
| cv10 | 有答案 | 1.0 | 1.0 | True | True | False |
| cv11 | 有答案 | 1.0 | 1.0 | True | True | False |
| cv15 | 有答案 | 1.0 | 1.0 | True | True | False |
| cv21 | 有答案 | 0.9852 | 1.0 | True | True | False |
| u01 | 无答案 | 0.433 | — | None | None | True |
| u02 | 无答案 | 0.4584 | — | None | None | True |
| u03 | 无答案 | 0.6756 | — | None | None | False |
| u04 | 无答案 | 0.6302 | — | None | None | True |
| u05 | 无答案 | 0.3569 | — | None | None | True |
| u06 | 无答案 | 0.6831 | — | None | None | True |
| u07 | 无答案 | 0.2685 | — | None | None | True |
| u08 | 无答案 | 0.1541 | — | None | None | False |
| u09 | 无答案 | 0.8462 | — | None | None | False |
| u10 | 无答案 | 0.0623 | — | None | None | True |
| u11 | 无答案 | 0.3451 | — | None | None | True |
| cu01 | 无答案 | 0.4805 | — | None | None | True |
| cu02 | 无答案 | 0.4991 | — | None | None | True |
| u12 | 无答案 | 0.5109 | — | None | None | True |
| u13 | 无答案 | 0.4539 | — | None | None | True |
| u14 | 无答案 | 0.4967 | — | None | None | True |
| u15 | 无答案 | 0.5297 | — | None | None | True |
| u16 | 无答案 | 0.6765 | — | None | None | False |
| u17 | 无答案 | 0.2791 | — | None | None | True |
| u18 | 无答案 | 0.209 | — | None | None | True |
| u19 | 无答案 | 0.5069 | — | None | None | False |
| u20 | 无答案 | 0.6901 | — | None | None | True |
| u21 | 无答案 | 0.2621 | — | None | None | True |
| u22 | 无答案 | 0.5644 | — | None | None | True |
| u23 | 无答案 | 0.5516 | — | None | None | True |
