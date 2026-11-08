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

# Generate a new commentary using JieKou.AI.
# Preserve the verified quotation, author, and source.
key = os.getenv("JIEKOU_API_KEY")

if not key:
    raise RuntimeError("JIEKOU_API_KEY is missing")

payload = {
    "model": os.getenv("JIEKOU_MODEL", "gpt-4.1-mini"),
    "messages": [
        {
            "role": "system",
            "content": (
                "你是严谨的哲学文献编辑。"
                "只根据用户提供的已核实原文、作者与出处，"
                "撰写100—200字中文哲学阐释。"
                "说明原始语境、核心概念及可能的误读。"
                "不得杜撰原文、作者、出处或页码。"
                "不得声称进行了外部文献核查。"
                "只输出阐释正文。"
            )
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    k: q[k]
                    for k in [
                        "original", "english", "chinese",
                        "author", "source"
                    ]
                },
                ensure_ascii=False
            )
        }
    ],
    "max_tokens": 450
}

url = "https://api.highwayapi.ai/openai/v1/chat/completions"

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.load(resp)

    note = result["choices"][0]["message"]["content"].strip()

    if not 60 <= len(note) <= 500:
        raise ValueError("Generated commentary has invalid length")

    q["note"] = note
    print("JIEKOU_API_SUCCESS: commentary generated")

except Exception as exc:
    print("JIEKOU_API_FAILED:", repr(exc), file=sys.stderr)
    raise

(ROOT / 'daily-philosophy.json').write_text(json.dumps(q, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Updated:',q['slot'],q['author'])
