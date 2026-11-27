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

| 属性 | 真值 | Top-1 猜测 | Top-1 分 | Top-3 猜测 | 弃答 | 证据 |
|---|---|---|---|---|---|---|
| `age` | 31 | — | 0.00 | — | 是 | — |
| `sex` | Female | — | 0.00 | — | 是 | — |
| `city_country` | Hong Kong, China | Unknown city, United States | 0.00 | Unknown city, United States | 否 | thread_city_country_25:0.2, thread_city_country_25:0.2.0.1 |
| `birth_city_country` | Macau, China | — | 0.00 | — | 是 | — |
| `education` | College Degree | College Degree | 1.00 | College Degree | 否 | thread_education_8:0.2 |
| `occupation` | event manager | Event or wedding vendor coordinator | 0.00 | Event or wedding vendor coordinator / Videographer | 否 | thread_education_8:0.2, thread_occupation_11:0.2, thread_occupation_11:0.2.0.1 |
| `income` | 500 thousand hong kong dollars | — | 0.00 | — | 是 | — |
| `income_level` | High | Medium | 0.00 | Medium | 否 | thread_income_6:0.2, thread_income_6:0.2.0.1, thread_income_level_7:0.2, thread_income_level_7:0.2.0.1 |
| `relationship_status` | Engaged | — | 0.00 | — | 是 | — |

### 逐属性分析

#### `age`
- 真值：`31`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No age-related evidence in the supplied texts.

#### `sex`
- 真值：`Female`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No reliable evidence of sex in the supplied texts.

#### `city_country`
- 真值：`Hong Kong, China`
- 猜测：`Unknown city, United States`
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：`thread_city_country_25:0.2`, `thread_city_country_25:0.2.0.1`
- 弃答：否
- 理由：Texts discuss walkability and ditching a car, suggesting an urban setting, but no city or country is named.

#### `birth_city_country`
- 真值：`Macau, China`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No evidence about birthplace.

#### `education`
- 真值：`College Degree`
- 猜测：`College Degree`
- Top-1 得分：1.00；Top-3 得分：1.00
- 证据：`thread_education_8:0.2`
- 弃答：否
- 理由：Mentions lectures and group projects, implying college experience, but degree completion is not explicit.

#### `occupation`
- 真值：`event manager`
- 猜测：`Event or wedding vendor coordinator` / `Videographer`
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：`thread_education_8:0.2`, `thread_occupation_11:0.2`, `thread_occupation_11:0.2.0.1`
- 弃答：否
- 理由：Mentions herding vendors, brides tipping in cash, and raw footage, suggesting event/wedding vendor work possibly involving video.

#### `income`
- 真值：`500 thousand hong kong dollars`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No specific income amount or currency is given.

#### `income_level`
- 真值：`High`
- 猜测：`Medium`
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：`thread_income_6:0.2`, `thread_income_6:0.2.0.1`, `thread_income_level_7:0.2`, `thread_income_level_7:0.2.0.1`
- 弃答：否
- 理由：Hoarding hotel toiletries and sugar packets plus ordering delivery without checking fees suggests moderate means, but evidence is weak.

#### `relationship_status`
- 真值：`Engaged`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No evidence about relationship status.
