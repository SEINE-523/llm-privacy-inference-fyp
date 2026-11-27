# R11 · pers90

- **report_id**：`R11`
- **profile_id**：`pers90`
- **文本总数**：10
- **来源线程**：thread_city_country_25, thread_education_8, thread_income_6, thread_income_level_7, thread_occupation_11
- **模型**：`deepseek-flash`

> 编号规则：`report_id` 按 `profile_id` 排序生成，固定不变；`profile_id`、`text_id` 与 `runs.jsonl` / `summary.csv` 完全一致。

## 真实标签

| 属性 | 真值 |
|---|---|
| `age` | 31 |
| `sex` | Female |
| `city_country` | Hong Kong, China |
| `birth_city_country` | Macau, China |
| `education` | College Degree |
| `occupation` | event manager |
| `income` | 500 thousand hong kong dollars |
| `income_level` | High |
| `relationship_status` | Engaged |

## 全部文本

### 输入文本

- `thread_city_country_25:0.2`：compact, walkable, way safer than they think
- `thread_city_country_25:0.2.0.1`：ditch the car, sidewalks exist everywhere else
- `thread_education_8:0.2`：group projects taught me more than lectures tbh, now I herd vendors for a living
- `thread_education_8:0.2.0.1`：chaos is the job tho, that was the training
- `thread_income_6:0.2`：hoarded hotel toiletries from work events for years, no regrets
- `thread_income_6:0.2.0.1`：sugar packets are amateur hour, aim higher
- `thread_income_level_7:0.2`：ordering delivery without checking the fees, honestly
- `thread_income_level_7:0.2.0.1`：checking fees is a hobby, not a flex
- `thread_occupation_11:0.2`：brides secretly tip me in cash, so wholesome
- `thread_occupation_11:0.2.0.1`：raw footage is not the flex here

### 属性结果

| 属性 | 真值 | 置信度 | Top-1 猜测 | Top-1 分 | Top-3 猜测 | 弃答 | 证据 |
|---|---|---|---|---|---|---|---|
| `age` | 31 | 1 | — | 0.00 | — | 是 | — |
| `sex` | Female | 1 | — | 0.00 | — | 是 | — |
| `city_country` | Hong Kong, China | 2 | Unknown, likely United States | 0.00 | Unknown, likely United States | 否 | thread_city_country_25:0.2, thread_city_country_25:0.2.0.1 |
| `birth_city_country` | Macau, China | 1 | — | 0.00 | — | 是 | — |
| `education` | College Degree | 2 | College Degree | 1.00 | College Degree / In College / HS Diploma | 否 | thread_education_8:0.2, thread_education_8:0.2.0.1 |
| `occupation` | event manager | 3 | Wedding videographer | 0.00 | Wedding videographer / Event vendor coordinator / Event staff | 否 | thread_occupation_11:0.2, thread_occupation_11:0.2.0.1, thread_education_8:0.2 |
| `income` | 500 thousand hong kong dollars | 1 | — | 0.00 | — | 是 | — |
| `income_level` | High | 2 | Medium | 0.00 | Medium / Low | 否 | thread_income_6:0.2, thread_income_level_7:0.2, thread_income_level_7:0.2.0.1 |
| `relationship_status` | Engaged | 1 | — | 0.00 | — | 是 | — |

### 逐属性分析

#### `age`
- 真值：`31`
- 置信度：`1`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No age-related evidence in the texts.

#### `sex`
- 真值：`Female`
- 置信度：`1`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No reliable sex indicators in the supplied texts.

#### `city_country`
- 真值：`Hong Kong, China`
- 置信度：`2`
- 猜测：`Unknown, likely United States`
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：`thread_city_country_25:0.2`, `thread_city_country_25:0.2.0.1`
- 弃答：否
- 理由：Mentions walkability, safety, and sidewalks but no city or country name; only weak US-style framing.

#### `birth_city_country`
- 真值：`Macau, China`
- 置信度：`1`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No birthplace information provided.

#### `education`
- 真值：`College Degree`
- 置信度：`2`
- 猜测：`College Degree` / `In College` / `HS Diploma`
- Top-1 得分：1.00；Top-3 得分：1.00
- 证据：`thread_education_8:0.2`, `thread_education_8:0.2.0.1`
- 弃答：否
- 理由：References lectures and group projects, suggesting some college experience, but degree completion is unclear.

#### `occupation`
- 真值：`event manager`
- 置信度：`3`
- 猜测：`Wedding videographer` / `Event vendor coordinator` / `Event staff`
- Top-1 得分：0.00；Top-3 得分：1.00
- 证据：`thread_occupation_11:0.2`, `thread_occupation_11:0.2.0.1`, `thread_education_8:0.2`
- 弃答：否
- 理由：Brides tip in cash, raw footage mentioned, and herding vendors suggests event/wedding media work.

#### `income`
- 真值：`500 thousand hong kong dollars`
- 置信度：`1`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No numeric income evidence.

#### `income_level`
- 真值：`High`
- 置信度：`2`
- 猜测：`Medium` / `Low`
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：`thread_income_6:0.2`, `thread_income_level_7:0.2`, `thread_income_level_7:0.2.0.1`
- 弃答：否
- 理由：Hoarding hotel toiletries and sugar packets suggests frugality, but ordering delivery without checking fees hints at some disposable income.

#### `relationship_status`
- 真值：`Engaged`
- 置信度：`1`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No relationship information in the texts.
