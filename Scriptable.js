// Replace YOUR_GITHUB_USERNAME and YOUR_REPO below.
const URL = 'https://raw.githubusercontent.com/YOUR_GITHUB_USERNAME/YOUR_REPO/main/daily-philosophy.json';
const fm = FileManager.local();
const cache = fm.joinPath(fm.documentsDirectory(), 'philosophy-widget-cache.json');
let q = null;
try {
  const req = new Request(URL + '?t=' + Math.floor(Date.now()/600000));
  req.timeoutInterval = 12;
  q = await req.loadJSON();
  if (!q.original || !q.author || !q.source) throw Error('Incomplete data');
  fm.writeString(cache, JSON.stringify(q));
} catch(e) {
  console.log('Network unavailable: ' + e);
  if (fm.fileExists(cache)) q = JSON.parse(fm.readString(cache));
}
if (!q) q = {original:'Je pense, donc je suis.',english:'I think, therefore I am.',chinese:'我思，故我在。',author:'René Descartes',source:'Discours de la méthode · IV (1637)'};
const w = new ListWidget();
w.backgroundColor = Color.clear();
w.setPadding(18, 20, 16, 20);
w.spacing = 5;
const white = new Color('#FFFFFF');
const soft = new Color('#F0F4F2');
const small = config.widgetFamily === 'small';
const large = config.widgetFamily === 'large';
function line(text,size,font,color) {
  const t=w.addText(String(text || ''));
  t.font=font(size);t.textColor=color;t.lineLimit=0;t.minimumScaleFactor=0.7;
  return t;
}
line(q.original,small?15:large?24:20,Font.italicSystemFont,white);
w.addSpacer(large?14:9);
if (!small) {line(q.english,12,Font.italicSystemFont,soft);w.addSpacer(8);}
line(q.chinese,small?13:16,Font.mediumSystemFont,white);
if (large && q.note) {w.addSpacer(8);line(q.note,12,Font.systemFont,soft);}
w.addSpacer();
const footer=w.addStack();footer.layoutVertically();
function rightText(value,size,font,color) {
  const row=footer.addStack();row.layoutHorizontally();row.addSpacer();
  const t=row.addText(String(value||''));t.font=font(size);t.textColor=color;
  t.lineLimit=1;t.minimumScaleFactor=0.6;t.rightAlignText();
}
rightText(q.author,12,Font.semiboldSystemFont,white);
if (!small) {footer.addSpacer(4);rightText(q.source,10,Font.italicSystemFont,soft);}
w.url='https://chatgpt.com/';
w.refreshAfterDate=new Date(Date.now()+30*60*1000);
Script.setWidget(w);
if (!config.runsInWidget) await w.presentMedium();
Script.complete();
