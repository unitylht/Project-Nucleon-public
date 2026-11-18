# Model bench: qwen3.5-35b-a3b, 20261031T100502Z

| Prompt | Passed | Passed with <= 4 calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |
|---|---|---|---|---|---|---|
| northside | 10/10 | 10/10 | 3 | 14.1 | 0 | 0 |
| bayview | 10/10 | 10/10 | 3 | 11.3 | 0 | 0 |
| harbourline | 10/10 | 10/10 | 3 | 12.9 | 0 | 0 |
| lakeside | 6/10 | 6/10 | 3 | 15.9 | 0 | 0 |
| mixed | 9/10 | 9/10 | 2 | 15.3 | 0 | 0 |

Runs where all five prompts passed with <= 4 tool calls each: **6 of 10**.
Tokens per prompt (median): 14096 prompt, 927 completion.
Nudge fired in 9 of 50 prompts. After it: resolved 4, asked_staff 5, still_empty 0.
Mixed prompt: nudge fired 1 of 10, cases created in 1.
