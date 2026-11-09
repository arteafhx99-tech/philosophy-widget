import datetime
import json
import os
import random
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TZ = datetime.timezone(datetime.timedelta(hours=8))
now = datetime.datetime.now(TZ)
slot = f"{now:%Y-%m-%d}-" + ('morning' if now.hour < 12 else 'evening')
quotes = json.loads((ROOT/'quotes.json').read_text(encoding='utf-8'))
quotes = [q for q in quotes if q.get('verified') is True and all(q.get(k) for k in ('original','english','chinese','author','source'))]
if not quotes:
    raise RuntimeError('No verified quotes available')
history_path = ROOT/'quote-history.json'
history = json.loads(history_path.read_text(encoding='utf-8')) if history_path.exists() else []
if not isinstance(history,list):
    history=[]
# Re-running the same morning/evening slot should not pick a different quotation.
current = next((x for x in reversed(history) if x.get('slot')==slot),None)
if current:
    matches=[x for x in quotes if x['original']==current.get('original') and x['author']==current.get('author')]
    candidates=matches or quotes
else:
    recent={(x.get('original'),x.get('author')) for x in history[-30:]}
    candidates=[x for x in quotes if (x['original'],x['author']) not in recent]
    if not candidates:
        recent={(x.get('original'),x.get('author')) for x in history[-max(0,len(quotes)-1):]}
        candidates=[x for x in quotes if (x['original'],x['author']) not in recent] or quotes
q=dict(random.SystemRandom().choice(candidates))
q.pop('verified',None)
q['updated_at']=now.isoformat()
q['slot']=slot
key=os.getenv('JIEKOU_API_KEY')
if not key:
    raise RuntimeError('JIEKOU_API_KEY is missing')
payload={
    'model':os.getenv('JIEKOU_MODEL','gpt-4.1-mini'),
    'messages':[
        {'role':'system','content':'你是严谨的哲学文献编辑。只根据用户提供的引文、作者、出处撰写100—200字中文哲学阐释，说明可能的思想语境与误读。不得杜撰原文、出处、页码，不得声称进行了外部核查。仅输出阐释正文。'},
        {'role':'user','content':json.dumps({k:q[k] for k in ('original','english','chinese','author','source')},ensure_ascii=False)}
    ],'max_tokens':450
}
req=urllib.request.Request('https://api.highwayapi.ai/openai/v1/chat/completions',data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
try:
    with urllib.request.urlopen(req,timeout=60) as resp:
        result=json.load(resp)
    note=result['choices'][0]['message']['content'].strip()
    if not 60<=len(note)<=500:
        raise ValueError('Generated commentary has invalid length')
    q['note']=note
    q['note_generated_at']=now.isoformat()
    print('JIEKOU_API_SUCCESS: commentary generated')
except Exception as exc:
    print('JIEKOU_API_FAILED:',repr(exc),file=sys.stderr)
    raise
(ROOT/'daily-philosophy.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if not current:
    history.append({'slot':slot,'original':q['original'],'author':q['author']})
history_path.write_text(json.dumps(history[-500:],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Updated:',slot,q['author'])
