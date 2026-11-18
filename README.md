# Nucleon

UNSW INFS3605, Term 3 2026 · Sandbox partner: Microsoft · Stream: Founder's Second Brain
(presented at Week 7 under the working name CreditEase)

Owners of small B2B manufacturers and wholesalers decide every credit exception themselves: a new customer who wants stock on terms, or a customer who asks for more days to pay. Nucleon lets staff type the request in a chat. An AI agent running on a local model gathers the facts from the business's records. The owner's saved rules, checked in code, then decide one of three outcomes:

- **approved by the agent**, when every rule passes;
- **staff asked for a missing fact**, when something the rules need is not known;
- **sent to the owner** with the evidence, when a rule fails or the owner wants to see it.

The model never decides by itself and never contacts a customer. The owner can pause the agent, agree with or override any decision, and see an audit trail for every case.

## Team

| Member | Role |
|---|---|
| Tony Tran | Product Owner |
| Chris Cheng | Scrum Master |
| Hanting Liu | Developer (full stack) |
| Hoang Duy Nguyen | Business Analyst |
| Thien Phu Do | Researcher |

## What is in this repository

This is a snapshot of the team's private development repository at commit `feb23de` (13 November 2026), the code and documents behind the final report. The 552 commits that led to it are listed in [docs/COMMIT-HISTORY.md](docs/COMMIT-HISTORY.md).

| Path | Contents |
|---|---|
| [PROMPTS.md](PROMPTS.md) | How the team used AI tools, and the instructions and tools given to the two assistants inside the product |
| [docs/PROMPT-REGISTER.md](docs/PROMPT-REGISTER.md) | Every version of the product's prompts, with dates and what changed |
| [docs/DECISIONS.md](docs/DECISIONS.md), [docs/ADAPTIVE-DECISION-AUTHORITY.md](docs/ADAPTIVE-DECISION-AUTHORITY.md) | Design decisions and the model of delegated authority |
| [docs/pov/](docs/pov/) | Proof-of-value work: feedback register, consent form, tester guide, facilitator runbook |
| [docs/handbook/](docs/handbook/) | User manual with screenshots, and the team's master document |
| [docs/INDEX.md](docs/INDEX.md) | Map of all documentation, with what is current and what is historical |
| `prototype/` | Records server (Python): business records, owner policy, decision engine, owner and staff pages, tests |
| `lab/` | MCP tool server that the chat agent uses, and its decision cards |
| `integrations/librechat/` | Chat front end configuration and patches, agent set-up scripts |
| `deploy/` | Scripts used to run and check the system on the developer's machine |

## How it was run

During the term the system ran on one machine: the model (Qwen3.5-35B-A3B) in LM Studio, LibreChat in Docker as the chat front end, and the Python records server, published through Cloudflare Access. That machine is no longer serving it, so the live links in the report do not work at present; the demonstration videos show the system running. [docs/ENGINEERING-INVENTORY-20261030.md](docs/ENGINEERING-INVENTORY-20261030.md) and [deploy/m3-local/README.md](deploy/m3-local/README.md) describe the set-up.

The decision engine and records server can be tested without the model:

```
cd prototype
python3 -m unittest discover -s . -p "test_*.py"
```

## Data and ethics

- Demonstrations and most tests use a fictional business (Northside Cafe, Lakeside Kiosk, Harbourline Catering and others are invented).
- The partner business's owner consented to the use of its ledger and to a real-records test instance. Customer names were replaced by numbers before the data reached the team. No real records are in this repository.
- The partner business and its owners are not named. Art of Gelato and its owner are named with permission.
- Access codes, logins and keys are not in this repository.
