"""Keeps the ADA Staff agent's instructions in one place: instructions_staff.txt (one paragraph per line) is the source; update_ada_agent_hints.js carries a
copy between its BEGIN/END markers (mongosh reads the script from stdin, so it cannot open the file), and so does the integration README. The model bench reads the text file.

    python3 integrations/librechat/agents/sync_instructions.py          # rewrite the block in the script
    python3 integrations/librechat/agents/sync_instructions.py --check  # exit 1 if the script differs from the text file
Python 3.9 compatible."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEXT, SCRIPT, README = HERE / 'instructions_staff.txt', HERE / 'update_ada_agent_hints.js', HERE.parent / 'README.md'
BLOCK = re.compile(r'(// BEGIN INSTRUCTIONS[^\n]*\n)(.*?)(// END INSTRUCTIONS)', re.S)
DOC = re.compile(r'(<!-- BEGIN STAFF INSTRUCTIONS[^\n]*-->\n)(.*?)(<!-- END STAFF INSTRUCTIONS -->)', re.S)


def paragraphs():
    return [line.strip() for line in TEXT.read_text(encoding='utf-8').splitlines() if line.strip()]


def instructions():
    """The text the agent gets: the paragraphs joined by a space (as the earlier agent scripts do)."""
    return ' '.join(paragraphs())


def block():
    return 'const LINES = [\n' + ''.join('  ' + json.dumps(p, ensure_ascii=False) + ',\n' for p in paragraphs()) + '];\n'


def synced():
    return BLOCK.sub(lambda m: m.group(1) + block() + m.group(3), SCRIPT.read_text(encoding='utf-8'), count=1)


def synced_readme():
    quote = '\n>\n'.join('> ' + p for p in paragraphs()) + '\n'
    return DOC.sub(lambda m: m.group(1) + quote + m.group(3), README.read_text(encoding='utf-8'), count=1)


def main(argv):
    if '--check' in argv:
        ok = synced() == SCRIPT.read_text(encoding='utf-8') and synced_readme() == README.read_text(encoding='utf-8')
        print('in sync' if ok else 'update_ada_agent_hints.js or the README differs from instructions_staff.txt: run sync_instructions.py')
        return 0 if ok else 1
    SCRIPT.write_text(synced(), encoding='utf-8')
    README.write_text(synced_readme(), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
