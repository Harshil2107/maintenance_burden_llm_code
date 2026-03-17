# Line-Level True Churn Report (Full Dataset)

**Metric 1**: `(Specific Lines Modified in 90 days) / (Lines Added)`
**Metric 2**: `(Total Change Events) / (Lines Added)` (Frequency)
**Scope**: All Repositories (Top 1000000 attempted)

## Results

| Metric | AI Code | Human Code |
| :--- | :--- | :--- |
| **Pairs Analyzed** | 294 | 291 |
| **Lines Contributed** | 249677 | 212469 |
| **Specific Lines Rewritten** | 160464 | 110862 |
| **Avg Churn Ratio** | **29.93%** | **38.32%** |
| **Total Change Events** | 6530 | 16236 |
| **Events Per Line** | **0.0262** | **0.0764** |

*Note: A ratio of 100% means every single line added was rewritten or deleted within 90 days.*
*Events Per Line indicates how frequently the added code blocks were modified.*
