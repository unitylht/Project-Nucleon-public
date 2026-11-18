# Model bench: qwen3.5-9b, 20261031T002128Z

| Prompt | Passed | Passed with <= 4 calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |
|---|---|---|---|---|---|---|
| northside | 10/10 | 10/10 | 3 | 21.0 | 0 | 0 |
| bayview | 10/10 | 10/10 | 4 | 22.9 | 0 | 0 |
| harbourline | 10/10 | 10/10 | 4 | 25.6 | 0 | 0 |
| lakeside | 10/10 | 10/10 | 4 | 23.4 | 0 | 0 |
| mixed | 9/10 | 9/10 | 3 | 24.2 | 0 | 0 |

Runs where all five prompts passed with <= 4 tool calls each: **9 of 10**.
Tokens per prompt (median): 18772 prompt, 1255 completion.
