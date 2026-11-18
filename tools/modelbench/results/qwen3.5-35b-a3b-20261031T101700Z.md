# Model bench: qwen3.5-35b-a3b, 20261031T101700Z

| Prompt | Passed | Passed with <= 4 calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |
|---|---|---|---|---|---|---|
| northside | 10/10 | 10/10 | 2 | 11.4 | 0 | 0 |
| bayview | 9/10 | 9/10 | 3 | 11.5 | 0 | 0 |
| harbourline | 10/10 | 10/10 | 2 | 9.8 | 0 | 0 |
| lakeside | 10/10 | 10/10 | 2 | 8.1 | 0 | 0 |
| mixed | 9/10 | 9/10 | 2 | 11.2 | 0 | 0 |

Runs where all five prompts passed with <= 4 tool calls each: **8 of 10**.
Tokens per prompt (median): 10259 prompt, 729 completion.
Nudge fired in 0 of 50 prompts. After it: resolved 0, asked_staff 0, still_empty 0.
Mixed prompt: nudge fired 0 of 10, cases created in 1.
