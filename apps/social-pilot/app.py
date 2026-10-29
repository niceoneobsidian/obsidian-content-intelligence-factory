#!/usr/bin/env python3
"""Loopback-only single-user social content pilot. Standard-library only."""
from __future__ import annotations
import json, os, re, sqlite3, uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HOST = "127.0.0.1"
PORT = int(os.environ.get("SOCIAL_PILOT_PORT", "8765"))
DB_PATH = Path(os.environ.get("SOCIAL_PILOT_DB", "data/social_pilot.sqlite3"))
ZERNIO_BASE = "https://zernio.com/api/v1"
PLATFORMS = ("tiktok", "facebook", "instagram", "twitter", "linkedin")
LABELS = {"tiktok":"TikTok", "facebook":"Facebook", "instagram":"Instagram",
          "twitter":"X", "linkedin":"LinkedIn"}

def account_map(raw=None):
    raw = os.environ.get("ZERNIO_ACCOUNT_IDS", "") if raw is None else raw
    result = {}
    for pair in raw.split(";"):
        if not pair.strip():
            continue
        if "=" not in pair:
            raise ValueError("Use platform=account_id for each mapping.")
        platform, account_id = (x.strip() for x in pair.split("=", 1))
        if platform not in PLATFORMS or not account_id:
            raise ValueError("Invalid platform/account mapping.")
        result[platform] = account_id
    return result

def validate_draft(data):
    content = str(data.get("content", "")).strip()
    platforms = data.get("platforms", [])
    media = str(data.get("media_url", "")).strip() or None
    scheduled = str(data.get("scheduled_for", "")).strip() or None
    if not content:
        raise ValueError("Post copy is required.")
    if not isinstance(platforms, list) or not platforms:
        raise ValueError("Select at least one platform.")
    if any(p not in PLATFORMS for p in platforms) or len(set(platforms)) != len(platforms):
        raise ValueError("Invalid or duplicated platform.")
    if media and not media.lower().startswith("https://"):
        raise ValueError("Media URL must use HTTPS.")
    if scheduled:
        try:
            dt = datetime.fromisoformat(scheduled.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Invalid scheduled date/time.") from exc
        if dt.tzinfo is None:
            raise ValueError("Scheduled date/time must include a timezone.")
        if dt <= datetime.now(dt.tzinfo):
            raise ValueError("Schedule time must be in the future.")
        scheduled = dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return content, platforms, media, scheduled

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS drafts(
          id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL,
          platforms_json TEXT NOT NULL, media_url TEXT, scheduled_for TEXT,
          status TEXT NOT NULL DEFAULT 'draft', provider_post_id TEXT,
          provider_response TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")

def drafts():
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM drafts ORDER BY id DESC").fetchall()
    output = []
    for row in rows:
        item = dict(row)
        item["platforms"] = json.loads(item.pop("platforms_json"))
        output.append(item)
    return output

def get_draft(draft_id):
    return next((d for d in drafts() if d["id"] == draft_id), None)

def set_status(draft_id, status, response=None, post_id=None):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""UPDATE drafts SET status=?, provider_response=COALESCE(?, provider_response),
          provider_post_id=COALESCE(?, provider_post_id), updated_at=? WHERE id=?""",
          (status, json.dumps(response) if response is not None else None, post_id, now, draft_id))

def save_draft(data):
    content, platforms, media, scheduled = validate_draft(data)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as db:
        cur = db.execute("""INSERT INTO drafts(content,platforms_json,media_url,scheduled_for,
          status,created_at,updated_at) VALUES(?,?,?,?, 'draft',?,?)""",
          (content, json.dumps(platforms), media, scheduled, now, now))
        return cur.lastrowid

def generate_copy(topic):
    if not topic.strip():
        raise ValueError("Enter a topic first.")
    endpoint = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    payload = {"model": os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:1.5b"),
      "stream": False, "prompt": "Write a useful, truthful NICEONE social post from this topic. "
      "Do not invent results or claim it has been published. Return only post copy and relevant hashtags.\n\n"
      + topic[:3000]}
    req = Request(endpoint, data=json.dumps(payload).encode(),
      headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urlopen(req, timeout=90) as resp:
            result = json.loads(resp.read().decode())
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("Ollama is unavailable. Start it, check the model, or write the post manually.") from exc
    copy = str(result.get("response", "")).strip()
    if not copy:
        raise RuntimeError("Local model returned an empty draft.")
    return copy

def publish(draft):
    if os.environ.get("SOCIAL_PILOT_ENABLE_PUBLISH", "").lower() != "true":
        raise RuntimeError("Publishing is disabled. Read the pilot README before explicitly enabling it.")
    key = os.environ.get("ZERNIO_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ZERNIO_API_KEY is not configured.")
    accounts = account_map()
    missing = [p for p in draft["platforms"] if not accounts.get(p)]
    if missing:
        raise RuntimeError("Missing Zernio account IDs for: " + ", ".join(LABELS[p] for p in missing))
    body = {"content": draft["content"],
      "platforms": [{"platform": p, "accountId": accounts[p]} for p in draft["platforms"]],
      "metadata": {"source":"niceone-ocif-local-pilot", "localDraftId":draft["id"]}}
    if draft["media_url"]:
        path = draft["media_url"].split("?", 1)[0].lower()
        kind = "video" if path.endswith((".mp4",".mov",".webm",".m4v")) else "image"
        body["mediaItems"] = [{"type":kind, "url":draft["media_url"]}]
    if draft["scheduled_for"]:
        body["scheduledFor"] = draft["scheduled_for"]
    else:
        body["publishNow"] = True
    req = Request(ZERNIO_BASE + "/posts", data=json.dumps(body).encode(),
      headers={"Authorization":"Bearer " + key, "Content-Type":"application/json",
               "Idempotency-Key":str(uuid.uuid4())}, method="POST")
    try:
        with urlopen(req, timeout=45) as resp:
            result = json.loads(resp.read().decode() or "{}")
            code = resp.status
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:1000]
        raise RuntimeError("Zernio HTTP " + str(exc.code) + ": " + detail) from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Publish result is uncertain. Check Zernio before retrying to avoid duplicates.") from exc
    if code == 207 or result.get("errors"):
        raise RuntimeError("Zernio reported a partial failure; inspect its dashboard before retrying. "
                           + json.dumps(result)[:1000])
    post = result.get("post", result)
    post_id = post.get("id") or post.get("postId") if isinstance(post, dict) else None
    return result, str(post_id) if post_id else None

def html_page():
    choices = "".join('<label class="pill"><input type="checkbox" name="platforms" value="' + p + '"> '
                      + LABELS[p] + '</label>' for p in PLATFORMS)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NICEONE Social Pilot</title><style>
:root{color-scheme:dark;--bg:#101318;--panel:#191f27;--line:#303945;--text:#eef2f7;--muted:#aab5c3;--accent:#b9f36a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}
main{max-width:1050px;margin:auto;padding:28px 18px 60px}.eyebrow{color:var(--accent);letter-spacing:.12em;font-size:12px;font-weight:700}
h1{font-size:clamp(28px,5vw,44px);line-height:1.1;margin:.4rem 0}h2{font-size:19px;margin:0 0 14px}p,.muted,small{color:var(--muted)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px;margin:16px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.banner{border:1px solid #786e40;background:#29271b;padding:12px 14px;border-radius:12px;margin:20px 0}
.field{display:block;font-size:13px;color:var(--muted);margin:12px 0 5px}
input[type=text],input[type=url],input[type=datetime-local],textarea{width:100%;padding:11px 12px;background:#0f1318;border:1px solid var(--line);border-radius:9px;color:var(--text);font:inherit}
textarea{min-height:145px;resize:vertical}.pills{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.pill{border:1px solid var(--line);border-radius:999px;padding:7px 11px}
button{border:0;border-radius:9px;padding:10px 14px;background:var(--accent);color:#17200d;font-weight:750;cursor:pointer}
button.secondary{background:#303945;color:var(--text)}button:disabled{opacity:.5}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.post{border-top:1px solid var(--line);padding:16px 0;overflow-wrap:anywhere}.status{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:2px 8px;font-size:12px;color:var(--accent)}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#0e1115;padding:10px;border-radius:8px;font-size:12px}@media(max-width:760px){.grid{grid-template-columns:1fr}.panel{padding:15px}}
</style></head><body><main><div class="eyebrow">NICEONE · INTERIM WORKFLOW</div><h1>Social Content Pilot</h1>
<p>Draft locally, review, approve, then optionally schedule or publish through Zernio.</p>
<div class="banner"><strong>Personal-use pilot, not production-ready.</strong> Runs on this Mac. Publishing is disabled until explicitly enabled. Review every post. Do not expose this server publicly.</div>
<div class="grid"><section class="panel"><h2>1 · Create a draft</h2><form id="form">
<label class="field" for="topic">Idea for local AI</label><input id="topic" type="text" maxlength="3000" placeholder="e.g. Why evidence-first AI automation matters">
<div class="actions"><button type="button" class="secondary" id="generate">Draft with Ollama</button></div>
<label class="field" for="content">Post copy (review and edit)</label><textarea id="content" required placeholder="Nothing is published when you generate or save a draft."></textarea>
<label class="field">Target platforms</label><div class="pills">""" + choices + """</div>
<label class="field" for="media">Public HTTPS media URL (optional)</label><input id="media" type="url" placeholder="https://your-host.example/video.mp4">
<label class="field" for="schedule">Schedule (optional, local time)</label><input id="schedule" type="datetime-local">
<small>Leave the schedule blank to publish now after approval. Media must be publicly reachable by the provider.</small>
<div class="actions"><button type="submit">Save draft</button></div></form><p id="message" role="status"></p></section>
<section class="panel"><h2>2 · Configuration</h2><p id="config">Checking settings…</p>
<p><strong>Workflow</strong></p><p class="muted">Draft → human approval → explicit publish/schedule → result stored locally. If a request times out, check Zernio before retrying.</p>
<p><a href="https://docs.zernio.com/" target="_blank" rel="noreferrer">Zernio API docs</a> · <a href="https://ollama.com/" target="_blank" rel="noreferrer">Ollama</a></p>
<p class="muted">This pilot does not yet use the verified OIS execution boundary. Temporary direct publishing is an explicit personal-use exception, not production architecture.</p></section></div>
<section class="panel"><h2>3 · Review queue</h2><div id="posts">Loading…</div></section></main>
<script>
const $=s=>document.querySelector(s);
function esc(v){return String(v==null?"":v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
async function api(path,body){const r=await fetch(path,{method:body?"POST":"GET",headers:body?{"Content-Type":"application/json"}:{},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||"Request failed");return d}
async function load(){try{const s=await api("/api/status");$("#config").innerHTML="Ollama model: <b>"+esc(s.ollama_model)+"</b><br>Zernio key: <b>"+(s.zernio_key?"configured":"not configured")+"</b><br>Publishing: <b>"+(s.publish_enabled?"enabled":"disabled by default")+"</b><br>Mapped accounts: "+esc(s.accounts.join(", ")||"none");
const d=await api("/api/drafts");$("#posts").innerHTML=d.drafts.length?d.drafts.map(p=>'<article class="post"><span class="status">'+esc(p.status)+'</span> <small>#'+p.id+' · '+esc(p.created_at)+'</small><p>'+esc(p.content)+'</p><small>Platforms: '+esc(p.platforms.join(", "))+(p.scheduled_for?' · '+esc(p.scheduled_for):'')+(p.media_url?' · media attached':'')+'</small>'+(p.provider_post_id?'<p>Provider ID: '+esc(p.provider_post_id)+'</p>':'')+(p.provider_response?'<details><summary>Provider response</summary><pre>'+esc(p.provider_response)+'</pre></details>':'')+'<div class="actions">'+(p.status==="draft"?'<button class="secondary" onclick="approve('+p.id+')">Approve</button>':'')+(p.status==="approved"?'<button onclick="sendPost('+p.id+')">Publish / schedule</button>':'')+'</div></article>').join(""):'<p>No drafts yet. Create your first post above.</p>'}catch(e){$("#posts").textContent=e.message}}
$("#form").addEventListener("submit",async e=>{e.preventDefault();$("#message").textContent="Saving…";try{const platforms=Array.from(document.querySelectorAll('input[name="platforms"]:checked')).map(x=>x.value);const local=$("#schedule").value;await api("/api/drafts",{content:$("#content").value,platforms,media_url:$("#media").value,scheduled_for:local?new Date(local).toISOString():null});$("#content").value="";$("#media").value="";$("#schedule").value="";$("#message").textContent="Draft saved. Not published.";await load()}catch(err){$("#message").textContent=err.message}});
$("#generate").addEventListener("click",async()=>{if(!$("#topic").value.trim()){ $("#message").textContent="Enter an idea first.";return }$("#generate").disabled=true;$("#message").textContent="Generating locally…";try{const r=await api("/api/generate",{topic:$("#topic").value});$("#content").value=r.content;$("#message").textContent="Generated locally. Review before saving."}catch(e){$("#message").textContent=e.message}finally{$("#generate").disabled=false}});
async function approve(id){try{await api("/api/drafts/"+id+"/approve",{});await load()}catch(e){alert(e.message)}}
async function sendPost(id){if(!confirm("Have you reviewed the caption, media, platforms, schedule and connected accounts? This action sends content externally."))return;try{const r=await api("/api/drafts/"+id+"/publish",{});alert(r.message);await load()}catch(e){alert(e.message);await load()}}
load();
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    server_version = "NiceoneSocialPilot/0.1"
    def send_json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)
    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("Request too large.")
        data = json.loads(self.rfile.read(length).decode() or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON object required.")
        return data
    def do_GET(self):
        if self.path == "/":
            raw = html_page().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/status":
            try: accounts = sorted(account_map())
            except ValueError: accounts = []
            self.send_json({"ollama_model":os.environ.get("OLLAMA_MODEL","qwen2.5-coder:1.5b"),
              "zernio_key":bool(os.environ.get("ZERNIO_API_KEY")),
              "publish_enabled":os.environ.get("SOCIAL_PILOT_ENABLE_PUBLISH","").lower()=="true",
              "accounts":accounts})
        elif self.path == "/api/drafts":
            self.send_json({"drafts":drafts()})
        else: self.send_json({"error":"Not found."},404)
    def do_POST(self):
        try:
            data = self.read_json()
            if self.path == "/api/drafts":
                draft_id = save_draft(data)
                self.send_json({"id":draft_id,"status":"draft"},201); return
            if self.path == "/api/generate":
                self.send_json({"content":generate_copy(str(data.get("topic","")))}); return
            match = re.fullmatch(r"/api/drafts/(\d+)/(approve|publish)",self.path)
            if not match:
                self.send_json({"error":"Not found."},404); return
            draft_id, action = int(match.group(1)), match.group(2)
            item = get_draft(draft_id)
            if not item:
                self.send_json({"error":"Draft not found."},404); return
            if action == "approve":
                if item["status"] != "draft": raise ValueError("Only a draft can be approved.")
                set_status(draft_id,"approved")
                self.send_json({"id":draft_id,"status":"approved"}); return
            if item["status"] != "approved":
                raise ValueError("Only an approved draft can be published or scheduled.")
            try:
                result, post_id = publish(item)
            except RuntimeError as exc:
                set_status(draft_id,"failed",{"error":str(exc)})
                raise
            state = "scheduled" if item["scheduled_for"] else "published"
            set_status(draft_id,state,result,post_id)
            self.send_json({"id":draft_id,"status":state,"message":"Zernio accepted the request. Verify the provider result and target accounts."})
        except (ValueError,json.JSONDecodeError) as exc:
            self.send_json({"error":str(exc)},400)
        except RuntimeError as exc:
            self.send_json({"error":str(exc)},502)
        except Exception:
            self.send_json({"error":"Unexpected error. Check the terminal and provider dashboard before retrying."},500)
    def log_message(self, fmt, *args):
        super().log_message(fmt,*args)

def main():
    init_db()
    server = ThreadingHTTPServer((HOST,PORT),Handler)
    print("NICEONE Social Pilot: http://127.0.0.1:" + str(PORT))
    print("SQLite: " + str(DB_PATH.resolve()))
    print("Publishing disabled unless SOCIAL_PILOT_ENABLE_PUBLISH=true.")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\nStopping.")
    finally: server.server_close()

if __name__ == "__main__":
    main()
