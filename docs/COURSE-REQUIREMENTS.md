# Agentic AI and Week 7 PoC requirements

Recorded: 16 October 2026, Australia/Sydney.

## Source and authority

These requirements come from two announcements by Sandeep pasted by Hanting on 16 October, and the attached `INFS3605_Week07_PoC_Demo_Template.pptx`, inspected including speaker notes. The receipt date is not an independently verified publication date. These specific instructions guide the upcoming design and PoC alongside the assessment outline.

This is a requirements record, not a claim that the team has implemented the features or approved a specific design.

## Agentic AI is a core design requirement

- Agentic AI must provide significant value in the solution. Ideally it is the core feature, but it need not be the entire solution.
- A generic chatbot or another dashboard that leaves the owner doing the same work does not satisfy the intended value proposition.
- Specify the business friction removed and the workflow the agent handles end to end or nearly so.
- Make the trigger, inputs, decisions, actions/tools, resulting business output and human approval points explicit.
- The pattern in the announcement is perceive, decide, act, and check with a human where judgement or approval matters.
- Identify where money, customer relationships or judgement require human involvement. Agentic does not mean unrestricted autonomous credit approval.
- Meet the user in a suitable existing channel, such as phone, SMS, email or voice. Confirm the actual channel used by the pilot business before selecting an integration. These are examples, not mandatory integrations to implement all at once.
- The Flex Week activity on invoking LLMs is the build foundation. It does not establish a requirement to train/fine-tune a model or to use cloud hosting.

## Implications for the current credit project

The next product decision must identify a credit-request workflow in which the agent takes work away from staff/the owner, rather than requiring them to assemble inputs and operate a dashboard step by step.

A candidate to investigate, **not a team-approved scope**:

1. A credit/extension request arrives through the selected channel or a clearly disclosed prototype input.
2. The agent extracts the request, retrieves relevant transactions, confirmed terms and owner context, and identifies missing information.
3. It obtains necessary missing input from the appropriate person, evaluates the request using calculated facts and authorised boundaries, and prepares the next action.
4. It handles authorised work, or requests a focused human decision at the specified approval point.
5. It records the outcome and creates or sends the appropriate response within explicit authority. Any simulated sending/integration must be clearly marked as mocked.

The exact approval boundaries, channel, business, data labels, MVP request type and test protocol remain unresolved. The requirements do not authorise autonomous financial decisions, live customer messages or access to real data.

For every proposed feature, record:

| Design item | Required explanation |
| --- | --- |
| Friction | What manual work disappears or becomes faster |
| Trigger | Which event starts the workflow |
| Inputs | What the agent perceives or retrieves, with source |
| Decisions | What it decides, checks or routes |
| Actions | Which tool, database operation or external operation it performs |
| Human control | Where approval is needed and who may give it |
| Outcome | What business result or completed artefact remains |
| Value evidence | Current workload, new interaction costs, errors and net benefit |
| Implementation status | What runs, what is mocked and what remains planned |

## Week 7 timing and deck

- **7 minutes total**, stopped at 7:00 even mid-demo.
- **5 minutes Q&A** after the presentation/demo.
- Suggested allocation: approximately **3 minutes slides and at least 4 minutes live demo** within the seven minutes.
- Use the supplied PoC template.
- Maximum **four content slides**, plus the title slide.

| Content slide | Required content | Template guide |
| --- | --- | --- |
| 1. Problem statement and evidence | Problem, intended user, and evidence from interviews, data or sponsor input | About 40 seconds |
| 2. High-level solution design and evidence it works | What the solution does, flow/screen, design decisions and supporting evidence | About 50 seconds |
| 3. Agentic feature | Business process, manual friction, trigger, agent decisions/actions, human check and outcome | About 60 seconds |
| 4. Build environment | Interface, storage, model invocation and connections, actual working scope versus mocks | About 30 seconds |

The file contains **nine slides total**: title, a delete-before-presenting instruction slide, the four content slides, a live-demo transition/script, backup, and Q&A. The supporting pages do not create permission for extra content slides. Delete the instruction slide and preserve the four-content-slide limit when preparing the final deck.

## Live demonstration and preparation

- Demonstrate the core feature working end to end with a realistic scenario.
- Agentic work should be the core feature or provide significant business value.
- Functionality takes priority over a polished/high-fidelity interface.
- Start the demo with the agentic feature. Have the account logged in and ready; avoid spending demonstration time on login.
- Show what triggers the agent, the moment it acts, the human approval point and the final result.
- Distinguish actual functionality from hard-coded, mocked or planned functionality.
- Use realistic fictional data for the course demo in line with the previously recorded Build Guide; “realistic” does not require uploading real customer data.
- Rehearse with a timer. Do not debug live if access fails.
- Prepare a short screen recording as a fallback. The template also provides backup screenshot space.
- Keep **PROMPTS.md** shared and accessible to the panel; the template explicitly asks for its repository/shared-folder location.
- The Q&A template prompts for a Week 8–9 user-testing plan: who will test, what they will do and what would demonstrate value.

## Current implementation decisions retained

Hanting’s local/home-server development choice remains current. No announcement here requires a specific stack, a cloud migration, a multi-agent framework or production-grade external-channel integration.

Hanting also instructed on 16 October to stop updating the HTML meeting brief because it is not being used and takes time to maintain. Shared project memory now uses Markdown records and the current-state source. The existing HTML is an archived snapshot, not a current project view.
