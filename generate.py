import json, os, sys, urllib.request, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
quotes = json.loads((ROOT / 'quotes.json').read_text(encoding='utf-8'))
quotes = [q for q in quotes if q.get('verified') is True]
if not quotes:
    raise RuntimeError('No verified quotes available')
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
# Rotate twice per day, using a deterministic index.
slot = (now.date() - datetime.date(2026, 1, 1)).days * 2 + (0 if now.hour < 12 else 1)
q = dict(quotes[slot % len(quotes)])
q.pop('verified', None)
q['updated_at'] = now.isoformat()
q['slot'] = f'{now:%Y-%m-%d}-' + ('morning' if now.hour < 12 else 'evening')

# Optional OpenAI API enhancement. Never replace the verified original/source.
key = os.getenv('OPENAI_API_KEY')
if key:
    payload = {
        'model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
        'input': [
            {'role':'system','content':'你是严谨的哲学文献编辑。只根据用户提供的已核实原文、作者与出处撰写100-200字中文阐释，说明语境与可能的误读。不得改写或杜撰原文、作者、出处，不得声称做了外部核查。只输出阐释正文。'},
            {'role':'user','content':json.dumps({k:q[k] for k in ['original','english','chinese','author','source']}, ensure_ascii=False)}
        ],
        'max_output_tokens': 350
    }
    req = urllib.request.Request('https://api.openai.com/v1/responses', data=json.dumps(payload).encode(), headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            result=json.load(resp)
        pieces=[c.get('text','') for item in result.get('output',[]) for c in item.get('content',[]) if c.get('type')=='output_text']
        note=''.join(pieces).strip()
        if 60 <= len(note) <= 500:
            q['note']=note
    except Exception as exc:
        print('API unavailable; retaining verified fallback note:',exc, file=sys.stderr)

(ROOT / 'daily-philosophy.json').write_text(json.dumps(q, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Updated:',q['slot'],q['author'])
