"""Conservative quote discovery: exact-match against retrieved public-domain texts.

AI suggests candidate passages; only literal substrings of a retrieved text are
eligible for automatic verification. Translation is explicitly AI-generated.
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
API = 'https://api.highwayapi.ai/openai/v1/chat/completions'
KEY = os.environ.get('JIEKOU_API_KEY', '')
MODEL = os.environ.get('JIEKOU_MODEL', 'gpt-4.1-mini')
TARGET = 5
# Original English-language works only. Gutenberg metadata/header is checked at runtime.
SOURCES = [
    {'id': 'gutenberg-5827', 'url': 'https://www.gutenberg.org/cache/epub/5827/pg5827.txt', 'author': 'Bertrand Russell', 'title': 'The Problems of Philosophy', 'language': 'en', 'check': 'The Problems of Philosophy'},
    {'id': 'gutenberg-34901', 'url': 'https://www.gutenberg.org/cache/epub/34901/pg34901.txt', 'author': 'John Stuart Mill', 'title': 'On Liberty', 'language': 'en', 'check': 'On Liberty'},
    {'id': 'gutenberg-3207', 'url': 'https://www.gutenberg.org/cache/epub/3207/pg3207.txt', 'author': 'Thomas Hobbes', 'title': 'Leviathan', 'language': 'en', 'check': 'Leviathan'},
]

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'PhilosophyWidgetResearch/1.0 (public-domain text verification)'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(2_500_000).decode('utf-8-sig', errors='replace')

def chat(messages):
    if not KEY:
        raise RuntimeError('JIEKOU_API_KEY missing')
    payload = {'model': MODEL, 'messages': messages, 'max_tokens': 1700, 'temperature': 0.3}
    req = urllib.request.Request(API, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers={'Authorization': 'Bearer '+KEY, 'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.load(resp)
    return out['choices'][0]['message']['content']

def normalize(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', s)).strip()

def load_json(path, fallback):
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return fallback

def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def parse_json(text):
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.I).strip()
    return json.loads(text)

def main():
    quotes_path = ROOT/'quotes.json'
    pending_path = ROOT/'pending-quotes.json'
    quotes = load_json(quotes_path, [])
    pending = load_json(pending_path, [])
    if not isinstance(quotes, list) or not isinstance(pending, list):
        raise ValueError('JSON databases must be arrays')
    existing = {normalize(q.get('original','')).casefold() for q in quotes + pending if isinstance(q,dict)}
    today = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')
    # Rotate starting source to avoid fixed bias.
    offset = dt.date.today().toordinal() % len(SOURCES)
    sources = SOURCES[offset:] + SOURCES[:offset]
    added = 0
    for source in sources:
        if added >= TARGET:
            break
        try:
            body = get(source['url'])
            if source['check'].casefold() not in body[:15000].casefold():
                print('SKIP: title mismatch', source['id'])
                continue
            # Extract Gutenberg book body, excluding legal boilerplate where possible.
            start = re.search(r'\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK[^\n]*\*\*\*', body, flags=re.I)
            end = re.search(r'\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK', body, flags=re.I)
            body = body[start.end():end.start()] if start and end else body[15000:-5000]
            # Rotating windows allow the corpus to be explored across days.
            cleaned = normalize(body)
            if len(cleaned) < 5000:
                print('SKIP: text too short', source['id'])
                continue
            span = 11500
            n = max(1, (len(cleaned)-span)//span)
            window = (dt.date.today().toordinal() + SOURCES.index(source)*17) % n
            excerpt = cleaned[window*span:window*span+span]
            answer = chat([
                {'role':'system', 'content': '你是文献引文候选提取器。只能从给出的英文原始文本中逐字复制短的、独立完整的哲学论断（每条约12-45个英文词）。绝不改写、拼接或补全。返回严格JSON数组，最多5项，每项 {"original":"逐字引文","chinese":"准确中文工作译文"}。如果没有合适引文，返回[]。不要添加其他文字。'},
                {'role':'user', 'content': f"作者：{source['author']}；书名：{source['title']}。请从以下原文摘取最多5条候选引文：\n{excerpt}"}
            ])
            candidates = parse_json(answer)
            if not isinstance(candidates, list):
                raise ValueError('Expected JSON array')
            for c in candidates[:5]:
                if added >= TARGET:
                    break
                if not isinstance(c, dict):
                    continue
                original = str(c.get('original','')).strip()
                chinese = str(c.get('chinese','')).strip()
                norm = normalize(original)
                if not (65 <= len(norm) <= 350 and 6 <= len(chinese) <= 350):
                    continue
                if norm.casefold() in existing:
                    continue
                # Exact text match after whitespace normalization. No semantic or LLM self-verification.
                if norm not in cleaned:
                    pending.append({'original':original,'author':source['author'],'source':source['title'],'source_url':source['url'],'status':'needs_review','reason':'Exact quotation not found in retrieved text','discovered_at':today})
                    existing.add(norm.casefold())
                    continue
                quote = {'original':original, 'english':original, 'chinese':chinese, 'author':source['author'], 'source':source['title']+' (Project Gutenberg, '+source['id']+')', 'source_url':source['url'], 'translation_note':'中文为AI工作译文，未经独立译本校勘', 'note':'原文已在所列公开文本中逐字匹配；中文译文及哲学语境仍需人工校订。', 'verified':True, 'verification_method':'exact_match_to_retrieved_public_domain_text', 'verified_at':today}
                quotes.append(quote)
                existing.add(norm.casefold())
                added += 1
        except Exception as e:
            print('Discovery source failed:', source['id'], repr(e), file=sys.stderr)
    save_json(quotes_path, quotes)
    save_json(pending_path, pending)
    print(f'DISCOVERY_COMPLETE: added={added}; total={len(quotes)}; pending={len(pending)}')

if __name__ == '__main__':
    main()
