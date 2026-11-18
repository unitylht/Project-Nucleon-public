# A small shared memory for Project Nucleon

Updated 16 October 2026: use this repository’s Markdown files as the shared project record and AI memory as a recall aid. Hanting stopped HTML maintenance because it was not being used and cost time. Preserve the existing HTML only as a historical snapshot.

| Option | Useful for | Limit in this project | Current choice |
| --- | --- | --- | --- |
| ChatGPT memory and chat history | Carrying preferences and context between conversations | Selective, changing recall; not a complete shared decision register; Claude and teammates do not automatically receive it | Supporting context |
| GitHub Markdown/JSON + revision history | One record for the team, coding assistants and future code | Someone or an assistant must commit reviewed updates; GitHub does not render arbitrary HTML as a page in the file view | Shared authority |
| Archived HTML brief | Historical reference only | No longer updated; browser notes remain local until exported and committed | Maintenance stopped 16 October |
| Obsidian over the same repository folder | Optional local reading, links and note editing | Team sync still requires a shared sync method; no need to maintain a second independent copy | Optional later |

## Low-effort update loop

1. After a meeting or meaningful AI session, write the new evidence and proposed changes in the dated meeting note.
2. Record actual confirmed decisions in DECISIONS.md with decision-maker, date and source. Keep hypotheses labelled.
3. Reconcile the current-state JSON, regenerate Markdown only and commit the relevant files together. Leave the archived HTML unchanged.
4. Before the next AI session, read the current files. If an assistant cannot access GitHub, attach the current-state file and relevant notes; do not assume the connector has refreshed or that chat memory has synchronised.

No vector database, automatic memory service or scheduled bot is required to make this work. The important properties are a clear current record, source links, explicit status, reviewable changes and an easy meeting view.

## Official sources checked

- [OpenAI: Memory in ChatGPT](https://help.openai.com/en/articles/8590148-memory-in-chatgpt): memory does not retain every conversation detail; contextual memory can change over time.
- [GitHub: About repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/about-repositories): repositories contain files and revision history and support project discussion/management.
- [Obsidian: How Obsidian stores data](https://obsidian.md/help/data-storage): notes are local Markdown files and can be edited with other tools.
- [GitHub: Invite collaborators](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository): a personal repository supports invitation by account or email.

These product descriptions were checked against official documentation. The recommendation and workflow are project-specific judgements, not guarantees of automatic synchronisation.
