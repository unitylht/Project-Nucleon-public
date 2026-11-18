# Model bench: qwen3.5-35b-a3b, 20261031T092704Z

| Prompt | Passed | Passed with <= 4 calls | Median calls | Median seconds | Provider errors | Says "approved" wrongly |
|---|---|---|---|---|---|---|
| northside | 9/10 | 9/10 | 3 | 14.7 | 0 | 0 |
| bayview | 10/10 | 8/10 | 4 | 14.1 | 0 | 0 |
| harbourline | 10/10 | 10/10 | 3 | 16.8 | 0 | 0 |
| lakeside | 8/10 | 8/10 | 4 | 16.4 | 0 | 0 |
| mixed | 10/10 | 10/10 | 2 | 13.2 | 0 | 0 |

Runs where all five prompts passed with <= 4 tool calls each: **6 of 10**.
Tokens per prompt (median): 14721 prompt, 1005 completion.
Nudge fired in 7 of 50 prompts. After it: resolved 3, asked_staff 3, still_empty 1.
Mixed prompt: nudge fired 1 of 10, cases created in 0.
