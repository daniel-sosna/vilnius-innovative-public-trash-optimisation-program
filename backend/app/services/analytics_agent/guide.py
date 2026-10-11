"""Load maintained semantic sections; never seed provider context with sample data."""
from pathlib import Path
import json
import re
from .registry import catalogue


def guide_directory():
    packaged = Path('/app/agent-domain')
    return packaged if packaged.is_dir() else Path(__file__).resolve().parents[4] / 'docs'


def guide():
    directory = guide_directory()
    guidance = (directory / 'agent-skills.md').read_text()
    sections = []
    for name in ('data-model.md', 'bin-days-columns.md'):
        path = directory / name
        if not path.exists() and name == 'bin-days-columns.md': path = directory / 'data' / name
        content = path.read_text()
        marked = re.findall(r'<!-- agent-runtime:start -->(.*?)<!-- agent-runtime:end -->', content, re.S)
        if not marked: raise ValueError('Runtime semantic section is missing')
        sections.extend(marked)
    return guidance + '\n\n' + '\n\n'.join(sections) + '\n\nTool catalogue:\n' + json.dumps(catalogue(), ensure_ascii=False, separators=(',', ':'))
