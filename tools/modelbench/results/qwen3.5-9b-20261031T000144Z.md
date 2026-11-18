# Model bench: qwen3.5-9b, 20261031T000144Z

| Prompt | Passed | Passed with <= 4 calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |
|---|---|---|---|---|---|---|
| northside | 3/3 | 3/3 | 3 | 26.0 | 0 | 0 |
| bayview | 3/3 | 3/3 | 4 | 23.2 | 0 | 0 |
| harbourline | 3/3 | 3/3 | 4 | 20.9 | 0 | 0 |
| lakeside | 3/3 | 3/3 | 4 | 21.4 | 0 | 0 |
| mixed | 3/3 | 2/3 | 3 | 31.8 | 0 | 0 |

Runs where all five prompts passed with <= 4 tool calls each: **2 of 3**.
Tokens per prompt (median): 18751 prompt, 1160 completion.
