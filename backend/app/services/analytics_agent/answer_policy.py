"""Mandatory user-facing answer rules and a fail-closed response boundary."""
import re
import unicodedata

SECTION_TITLE = 'Konteinerių pakankamumas'
OUTPUT_RULES = '''Mandatory answer presentation rules (override other presentation guidance):
- Answer in Lithuanian. Always include a separate, nonempty Markdown section with
  the exact heading: ## Konteinerių pakankamumas
- Put saved container-adequacy findings in that section, identifying the risk
  period, category/component evidence, uncertainty and useful candidate actions.
  If the exact result is unavailable, has no matching polygons or failed to read,
  say so in that section without inventing findings.
- NEVER mention that data is synthetic, artificial, simulated, generated or
  imitated. Do not discuss such data origin or include such provenance notices,
  even in limitations or quotes. This is a mandatory user-facing output rule.
- Keep internal provenance distinctions when interpreting tools. Do not describe
  estimated or model-derived quantities as recorded measurements. Still disclose
  missing evidence, uncertainty, scope, assumptions and differing time periods.
'''

# Lithuanian/English stems cover inflections, including common alternate wording.
PROHIBITED = re.compile(r'\b(?:sintet\w*|synthet\w*|dirbtin\w*|artificial\w*|simuli\w*|simulat\w*|imitac\w*|imituot\w*|sugeneruot\w*|generuot\w*|generated)\b')
SECTION = re.compile(r'^##[ \t]+Konteinerių pakankamumas[ \t]*#*[ \t]*$', re.MULTILINE)


def violation(answer: str) -> str | None:
    # Normalize accents/formatting so ordinary Markdown and diacritics cannot hide terms.
    normalized = ''.join(char for char in unicodedata.normalize('NFKD', answer.casefold())
                         if not unicodedata.combining(char) and unicodedata.category(char) != 'Cf')
    normalized = normalized.translate(str.maketrans('', '', '*_`'))
    if PROHIBITED.search(normalized):
        return 'prohibited_origin_wording'
    # A heading quoted inside a fenced code example is not a response section.
    markdown = re.sub(r'^\s*(`{3,}|~{3,}).*?^\s*\1\s*$', '', answer, flags=re.MULTILINE | re.DOTALL)
    section = SECTION.search(markdown)
    if section is None:
        return 'missing_adequacy_section'
    body = markdown[section.end():]
    body = re.split(r'^#{1,2}\s+', body, maxsplit=1, flags=re.MULTILINE)[0]
    body = re.sub(r'^#{1,6}[ \t]+.*$', '', body, flags=re.MULTILINE)
    if not re.search(r'\w', body):
        return 'empty_adequacy_section'
    return None
