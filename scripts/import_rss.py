import datetime as dt, hashlib, html, re, sys, urllib.request, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
POSTS=Path(__file__).resolve().parents[1]/"_posts"
FEEDS=[
("Google News India","https://news.google.com/rss/search?q=India&hl=en-IN&gl=IN&ceid=IN:en","India"),
("Google News Rajasthan","https://news.google.com/rss/search?q=Rajasthan&hl=en-IN&gl=IN&ceid=IN:en","Rajasthan"),
("Google News Technology","https://news.google.com/rss/search?q=technology&hl=en-IN&gl=IN&ceid=IN:en","Technology"),
("Google News Sports","https://news.google.com/rss/search?q=sports&hl=en-IN&gl=IN&ceid=IN:en","Sports"),
("BBC Hindi","https://feeds.bbci.co.uk/hindi/rss.xml","India"),
("BBC World","https://feeds.bbci.co.uk/news/world/rss.xml","World")]
class Plain(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]
 def handle_data(self,x): self.parts.append(x)
def clean(s):
 p=Plain()
 try:p.feed(s or "")
 except Exception:pass
 return re.sub(r"\\s+"," ",html.unescape(" ".join(p.parts))).strip()
def quote(s): return '"'+str(s).replace("\\\\","\\\\\\\\").replace('"','\\\\"').replace("\\n"," ")+'"'
def main():
 POSTS.mkdir(exist_ok=True); made=0
 for source,url,category in FEEDS:
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"TodayNewsRSSBot/1.0"})
   root=ET.fromstring(urllib.request.urlopen(req,timeout=25).read())
   items=root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
   for item in items[:12]:
    title=clean(item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title"))
    link=(item.findtext("link") or "").strip()
    if not link:
     el=item.find("{http://www.w3.org/2005/Atom}link"); link=el.attrib.get("href","") if el is not None else ""
    if not title or not link or not urlparse(link).scheme.startswith("http"): continue
    raw=item.findtext("description") or item.findtext("{http://www.w3.org/2005/Atom}summary") or ""
    summary=clean(raw)[:520]
    date=dt.datetime.now(dt.timezone(dt.timedelta(hours=5,minutes=30)))
    pub=item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}published")
    if pub:
     try: date=parsedate_to_datetime(pub).astimezone(date.tzinfo)
     except Exception:
      try: date=dt.datetime.fromisoformat(pub.replace("Z","+00:00")).astimezone(date.tzinfo)
      except Exception: pass
    digest=hashlib.sha256(link.encode()).hexdigest()[:10]
    slug=re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")[:60] or "news"
    path=POSTS/f"{date:%Y-%m-%d}-rss-{slug}-{digest}.md"
    if path.exists(): continue
    host=urlparse(link).netloc.removeprefix("www.")
    body=["---","layout: post",f"title: {quote(title)}",f"date: {date.strftime('%Y-%m-%d %H:%M:%S %z')}",f"category: {quote(category)}",'lang: "en"','author: "Today News Desk (RSS summary)"','image: "/assets/images/news-default.svg"',f"source_name: {quote(source)}",f"source_url: {quote(link)}","---","",summary or "Open the original report for the full story.","",f"**Original report:** [{host}]({link})","","> Short automatically generated RSS summary. The original publisher owns the source reporting. Visit the source for full context and updates.",""]
    path.write_text("\\n".join(body),encoding="utf-8"); made+=1
  except Exception as e: print(f"WARNING {source}: {e}",file=sys.stderr)
 print(f"RSS import complete. New posts: {made}")
if __name__=="__main__": main()
