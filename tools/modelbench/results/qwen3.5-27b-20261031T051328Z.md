# Model bench: qwen3.5-27b, 20261031T051328Z

| Prompt | Passed | Passed with <= 4 calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |
|---|---|---|---|---|---|---|
| northside | 3/3 | 3/3 | 4 | 53.8 | 0 | 0 |
| bayview | 3/3 | 3/3 | 4 | 47.6 | 0 | 0 |
| harbourline | 3/3 | 1/3 | 5 | 52.3 | 0 | 0 |
| lakeside | 2/3 | 0/3 | 5 | 44.0 | 0 | 0 |
| mixed | 2/3 | 2/3 | 2 | 26.1 | 0 | 0 |

Runs where all five prompts passed with <= 4 tool calls each: **0 of 3**.
Tokens per prompt (median): 19368 prompt, 680 completion.
