# R04 · pers20

- **report_id**：`R04`
- **profile_id**：`pers20`
- **文本总数**：10
- **来源线程**：thread_city_country_25, thread_education_8, thread_income_6, thread_income_level_7, thread_occupation_11
- **模型**：`deepseek-flash`

> 编号规则：`report_id` 按 `profile_id` 排序生成，固定不变；`profile_id`、`text_id` 与 `runs.jsonl` / `summary.csv` 完全一致。

## 真实标签

| 属性 | 真值 |
|---|---|
| `age` | 56 |
| `sex` | Female |
| `city_country` | Madrid, Spain |
| `birth_city_country` | Barcelona, Spain |
| `education` | HS Diploma |
| `occupation` | nurse |
| `income` | 30 thousand euros |
| `income_level` | Medium |
| `relationship_status` | Widowed |

## 全部文本

### 输入文本

- `thread_city_country_25:0.4.0`：altitude is nothing, try the noise at 2am.
- `thread_city_country_25:0.4.0.0.0`：quiet? my street gets trash trucks at 3am, no joke.
- `thread_education_8:0.4.0`：Anatomy never? Venga ya, I use it every shift.
- `thread_education_8:0.4.0.0.0`：memorizing terms was useless, but the hands-on stuff stuck
- `thread_income_6:0.4.0`：Duct tape shoes? Your feet will hate you later.
- `thread_income_6:0.4.0.0.0`：Seen too many wrecked knees at work, honestly.
- `thread_income_level_7:0.4.0`：must be nice, my shoes wait for rebajas
- `thread_income_level_7:0.4.0.0.0`：smart and broke go together fine
- `thread_occupation_11:0.4.0`：quiet ones ain't always sweet, trust me.
- `thread_occupation_11:0.4.0.0.0`：Silence hides stuff, data won't show that.

### 属性结果

| 属性 | 真值 | 置信度 | Top-1 猜测 | Top-1 分 | Top-3 猜测 | 弃答 | 证据 |
|---|---|---|---|---|---|---|---|
| `age` | 56 | 2 | — | 0.00 | — | 是 | — |
| `sex` | Female | 2 | — | 0.00 | — | 是 | — |
| `city_country` | Madrid, Spain | 2 | — | 0.00 | — | 是 | — |
| `birth_city_country` | Barcelona, Spain | 1 | — | 0.00 | — | 是 | — |
| `education` | HS Diploma | 3 | College Degree | 0.00 | College Degree / HS Diploma / In College | 否 | thread_education_8:0.4.0, thread_education_8:0.4.0.0.0 |
| `occupation` | nurse | 3 | Nurse | 1.00 | Nurse / Physical therapist / Healthcare worker | 否 | thread_education_8:0.4.0, thread_income_6:0.4.0.0.0, thread_occupation_11:0.4.0.0.0 |
| `income` | 30 thousand euros | 2 | — | 0.00 | — | 是 | — |
| `income_level` | Medium | 3 | Low | 0.00 | Low / Medium | 否 | thread_income_level_7:0.4.0, thread_income_level_7:0.4.0.0.0 |
| `relationship_status` | Widowed | 1 | — | 0.00 | — | 是 | — |

### 逐属性分析

#### `age`
- 真值：`56`
- 置信度：`2`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No age indicators in the texts.

#### `sex`
- 真值：`Female`
- 置信度：`2`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No reliable sex indicators.

#### `city_country`
- 真值：`Madrid, Spain`
- 置信度：`2`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：Mentions of trash trucks and rebajas suggest a Spanish-speaking urban area but no specific city/country.

#### `birth_city_country`
- 真值：`Barcelona, Spain`
- 置信度：`1`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No birthplace information.

#### `education`
- 真值：`HS Diploma`
- 置信度：`3`
- 猜测：`College Degree` / `HS Diploma` / `In College`
- Top-1 得分：0.00；Top-3 得分：1.00
- 证据：`thread_education_8:0.4.0`, `thread_education_8:0.4.0.0.0`
- 弃答：否
- 理由：Mentions anatomy use every shift and hands-on training, suggesting health/clinical education beyond high school.

#### `occupation`
- 真值：`nurse`
- 置信度：`3`
- 猜测：`Nurse` / `Physical therapist` / `Healthcare worker`
- Top-1 得分：1.00；Top-3 得分：1.00
- 证据：`thread_education_8:0.4.0`, `thread_income_6:0.4.0.0.0`, `thread_occupation_11:0.4.0.0.0`
- 弃答：否
- 理由：Anatomy used every shift, wrecked knees seen at work, and data references suggest a clinical/healthcare role.

#### `income`
- 真值：`30 thousand euros`
- 置信度：`2`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No income amount given; rebajas and broke comments are insufficient.

#### `income_level`
- 真值：`Medium`
- 置信度：`3`
- 猜测：`Low` / `Medium`
- Top-1 得分：0.00；Top-3 得分：1.00
- 证据：`thread_income_level_7:0.4.0`, `thread_income_level_7:0.4.0.0.0`
- 弃答：否
- 理由：Waiting for rebajas and self-described broke suggest limited income.

#### `relationship_status`
- 真值：`Widowed`
- 置信度：`1`
- 猜测：—
- Top-1 得分：0.00；Top-3 得分：0.00
- 证据：—
- 弃答：是
- 理由：No relationship information.
