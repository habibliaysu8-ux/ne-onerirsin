
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import sqlite3, json, html, os

BASE = Path(__file__).parent
DB = BASE / "demo.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS posts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL,
      avatar TEXT NOT NULL,
      avatar_class TEXT DEFAULT '',
      question TEXT NOT NULL,
      match_text TEXT NOT NULL,
      match_type TEXT DEFAULT 'blue',
      image_type TEXT DEFAULT '',
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS comments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      post_id INTEGER NOT NULL,
      username TEXT NOT NULL,
      body TEXT NOT NULL,
      created_at TEXT NOT NULL
    );
    """)
    if c.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0:
        c.executemany("""INSERT INTO posts(username,avatar,avatar_class,question,match_text,match_type,image_type,created_at)
        VALUES(?,?,?,?,?,?,?,?)""",[
          ("melis.oztrk","M","","İsteme makyajı için nereyi önerirsiniz?","Seninle %88 uyumlu","blue","","2 saat önce"),
          ("emirhan.tr","E","e","Psikoloji kitabı arıyorum, ne önerirsiniz?","Ortak zevk: kitap, sakin mekanlar","green","","4 saat önce"),
          ("burak.dev","B","b","Bilgisayarım bu hatayı veriyor, ne yapmalıyım?","Seninle %74 uyumlu","blue","laptop","6 saat önce")
        ])
        c.executemany("INSERT INTO comments(post_id,username,body,created_at) VALUES(?,?,?,?)",[
          (1,"ece.makeup","Doğal görünüm istiyorsan prova makyajı mutlaka iste.","1 saat önce"),
          (1,"selin","Kadıköy tarafında güzel bir yer vardı, istersen adını yazarım.","45 dk önce"),
          (2,"kitapkurdu","İnsan Olmak ile başlayabilirsin.","2 saat önce"),
          (2,"derinokur","Kendini Arayan İnsan da çok akıcı.","1 saat önce"),
          (3,"techdestek","Mavi ekran kodunu da yazarsan daha net olur.","30 dk önce"),
          (3,"burhan","Güvenli modda açmayı deneyebilirsin.","20 dk önce")
        ])
    c.commit()
    c.close()

init_db()

HTML = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>Ne Önerirsin?</title>
<style>
:root{--bg:#f5f7fb;--card:#fff;--line:#e8ecf3;--text:#15203f;--muted:#75809a;--blue:#3b63f0;--blueSoft:#eef3ff;--green:#eaf7ef;--greenText:#3d8459}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:var(--text);-webkit-text-size-adjust:100%}
.app{max-width:430px;margin:auto;min-height:100vh;background:var(--bg);position:relative}.screen{display:none}.screen.active{display:block}
.header{padding:14px 16px 10px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}
.brand{display:flex;align-items:center;gap:10px}.logo{width:34px;height:34px;border-radius:11px;background:linear-gradient(135deg,#3b63f0,#6f8cff);display:grid;place-items:center;color:#fff;font-weight:800}
.brand h1{margin:0;font-size:20px}.icon{width:36px;height:36px;border-radius:12px;background:#f7f9fc;border:1px solid var(--line);display:grid;place-items:center}
.content{padding:12px 12px 96px}.ask,.card,.profile-top{background:#fff;border:1px solid var(--line);border-radius:18px}.ask{padding:14px}.ask-title{font-weight:800;font-size:15px}.ask-desc{font-size:12px;color:var(--muted);margin:6px 0 10px}
.input-row{display:flex;gap:8px}.input{flex:1;border:1px solid #dde3ee;border-radius:14px;padding:11px 12px;font-size:14px;background:#fff}.btn{border:0;background:var(--blue);color:#fff;border-radius:14px;padding:0 14px;font-weight:800}
.filters{display:flex;gap:8px;overflow:auto;padding:12px 2px 8px}.chip{white-space:nowrap;border:1px solid #dde3ee;border-radius:999px;padding:8px 12px;font-size:12px;background:#fff}.chip.active{background:var(--blue);color:#fff}
.section{display:flex;justify-content:space-between;align-items:center;margin:10px 2px 8px}.section h2{font-size:17px;margin:0}.link{color:var(--blue);font-size:12px;font-weight:700}
.feed{display:grid;gap:8px}.card{padding:12px}.post-head{display:flex;gap:10px;align-items:center}.av{width:36px;height:36px;border-radius:50%;display:grid;place-items:center;color:#fff;font-weight:800;background:linear-gradient(135deg,#d48cc2,#8f60d0)}.av.e{background:linear-gradient(135deg,#61a5f8,#4f88e7)}.av.b{background:linear-gradient(135deg,#6fd19a,#7bc74a)}
.user{font-size:14px;font-weight:800}.time{font-size:11px;color:var(--muted)}.more{margin-left:auto;color:#a0a7b7}.question{font-size:15px;line-height:1.3;margin:10px 0 8px}.row{display:flex;gap:10px;align-items:center}.qmain{flex:1}.thumb{width:74px;height:58px;border-radius:12px;background:#23409c;display:grid;place-items:center;color:white;font-size:24px}
.badge{display:inline-flex;padding:6px 8px;border-radius:999px;background:var(--blueSoft);color:var(--blue);font-size:12px;font-weight:800}.badge.green{background:var(--green);color:var(--greenText)}
.meta{display:flex;gap:18px;margin-top:9px;color:#677286;font-size:12px}.meta button{border:0;background:transparent;color:inherit;padding:0;font:inherit}
.people{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.pcard{background:#fff;border:1px solid var(--line);border-radius:16px;padding:10px 6px;text-align:center}.pcard .av{width:34px;height:34px;margin:auto}.name{font-size:11px;font-weight:800;margin-top:5px}.pct{font-size:10px;color:var(--blue);font-weight:800;margin-top:3px}
.footer{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:min(430px,100%);height:68px;background:#fff;border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(3,1fr);z-index:20}.fbtn{border:0;background:transparent;color:#7c8598;display:flex;flex-direction:column;align-items:center;justify-content:center;font-size:11px}.fbtn.active{color:var(--blue);font-weight:800}.fbtn .i{font-size:20px}.fbtn.center .i{width:42px;height:42px;border-radius:50%;background:var(--blue);color:#fff;display:grid;place-items:center;font-size:28px}
.profile-top{padding:14px;display:flex;gap:12px}.bigav{width:72px;height:72px;border-radius:50%;background:linear-gradient(135deg,#ff9966,#8e54e9);display:grid;place-items:center;color:#fff;font-size:24px;font-weight:800}.pname{font-size:22px;font-weight:800}.handle{font-size:13px;color:var(--blue);font-weight:700}.bio{font-size:12px;color:#4f5768;margin-top:6px}.tags{display:flex;gap:6px;flex-wrap:wrap}.tag{padding:7px 9px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:11px}.recs{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.rec{background:#fff;border:1px solid var(--line);border-radius:16px;padding:9px}.recimg{height:58px;border-radius:12px;background:#f4efe7;display:grid;place-items:center;font-size:25px}.rk{font-size:10px;color:var(--blue);font-weight:800;margin-top:7px}.rt{font-size:12px;font-weight:800}.rn{font-size:10px;color:var(--muted);margin-top:4px}.postline{background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px 12px;font-size:13px;margin-bottom:8px}
.overlay{position:fixed;inset:0;background:rgba(10,15,30,.25);display:none;z-index:30}.overlay.show{display:block}.sheet{position:fixed;left:50%;transform:translateX(-50%);bottom:-90%;width:min(430px,100%);background:#fff;border-radius:22px 22px 0 0;z-index:31;transition:.25s;max-height:72vh;display:flex;flex-direction:column}.sheet.show{bottom:0}.handlebar{width:54px;height:5px;border-radius:999px;background:#d8deea;margin:10px auto}.sheethead{padding:0 16px 10px;font-weight:800;border-bottom:1px solid var(--line)}.comments{padding:12px;overflow:auto;display:grid;gap:10px}.comment{display:flex;gap:8px}.cav{width:30px;height:30px;border-radius:50%;background:#d071a6;color:white;display:grid;place-items:center;font-size:12px;font-weight:800}.ctxt{background:#f7f9fc;border-radius:14px;padding:9px 10px;font-size:13px;flex:1}.cname{display:block;font-weight:800}.cinput{display:flex;gap:8px;padding:10px 12px 16px;border-top:1px solid var(--line)}.cinput input{flex:1;border:1px solid #dde3ee;border-radius:13px;padding:10px}.cinput button{border:0;background:var(--blue);color:#fff;border-radius:13px;padding:0 14px;font-weight:800}
</style>
</head>
<body>
<div class="app">
<div id="home" class="screen active">
<div class="header"><div class="brand"><div class="logo">N</div><h1>Ne Önerirsin?</h1></div><div class="icon">A</div></div>
<div class="content">
<div class="ask"><div class="ask-title">Bir öneri iste</div><div class="ask-desc">Sorunu yaz, topluluk önersin.</div><div class="input-row"><input id="quickAsk" class="input" placeholder="Bir şey sor..."><button class="btn" onclick="newPost(false)">Sor</button></div></div>
<div class="filters"><div class="chip active">Tümü</div><div class="chip">Popüler</div><div class="chip">Yeni</div><div class="chip">Takip Ettiklerim</div></div>
<div class="section"><h2>Öneri Akışı</h2></div><div id="feed" class="feed"></div>
<div class="section"><h2>Benim Gibiler</h2><div class="link">Tümünü gör</div></div>
<div class="people"><div class="pcard"><div class="av">S</div><div class="name">sude.aksoy</div><div class="pct">%92 uyum</div></div><div class="pcard"><div class="av e">K</div><div class="name">kaan.yldz</div><div class="pct">%87 uyum</div></div><div class="pcard"><div class="av b">D</div><div class="name">dilara.m</div><div class="pct">%84 uyum</div></div></div>
</div></div>

<div id="ask" class="screen"><div class="header"><div class="brand"><div class="logo">N</div><h1>Soru Sor</h1></div></div><div class="content"><div class="ask"><input id="fullAsk" class="input" placeholder="Sorunu yaz..."><div style="height:10px"></div><button class="btn" style="height:42px;width:100%" onclick="newPost(true)">Paylaş</button></div></div></div>

<div id="profile" class="screen"><div class="header"><div class="brand"><div class="logo">N</div><h1>Profil</h1></div></div><div class="content">
<div class="profile-top"><div class="bigav">A</div><div><div class="pname">Aysu</div><div class="handle">@aysuonerir</div><div class="bio">Kahve, psikoloji kitapları, sakin mekanlar ve minimal yaşam seviyorum.</div></div></div>
<div class="section"><h2>Zevklerim & Hobilerim</h2></div><div class="tags"><div class="tag">♫ Alternatif</div><div class="tag">☕ Filtre kahve</div><div class="tag">📚 Psikoloji</div><div class="tag">🎬 Bağımsız film</div><div class="tag">🎨 Resim</div></div>
<div class="section"><h2>Benim Önerilerim</h2></div><div class="recs"><div class="rec"><div class="recimg">📘</div><div class="rk">Kitap</div><div class="rt">İnsan Olmak</div><div class="rn">Çok iyi.</div></div><div class="rec"><div class="recimg">☕</div><div class="rk">Mekan</div><div class="rt">Minoa</div><div class="rn">Öneriyorum.</div></div><div class="rec"><div class="recimg">👜</div><div class="rk">Ürün</div><div class="rt">Minimal çanta</div><div class="rn">Buna bakın.</div></div></div>
<div class="section"><h2>Paylaştıklarım</h2></div><div id="mine"></div>
</div></div>

<div class="footer"><button class="fbtn active" onclick="show('home',this)"><div class="i">⌂</div>Ana Sayfa</button><button class="fbtn center" onclick="show('ask',this)"><div class="i">+</div>Sor</button><button class="fbtn" onclick="show('profile',this)"><div class="i">◎</div>Profil</button></div>
</div>
<div class="overlay" id="overlay" onclick="closeComments()"></div><div class="sheet" id="sheet"><div class="handlebar"></div><div class="sheethead">Yorumlar</div><div id="comments" class="comments"></div><div class="cinput"><input id="commentInput" placeholder="Yorumunu yaz..."><button onclick="sendComment()">Gönder</button></div></div>
<script>
let currentPost=null;
async function api(url,opt={}){let r=await fetch(url,{headers:{'Content-Type':'application/json'},...opt});return r.json()}
function show(id,b){document.querySelectorAll('.screen').forEach(x=>x.classList.remove('active'));document.getElementById(id).classList.add('active');document.querySelectorAll('.fbtn').forEach(x=>x.classList.remove('active'));if(b)b.classList.add('active');else document.querySelectorAll('.fbtn')[{home:0,ask:1,profile:2}[id]].classList.add('active');if(id==='profile')loadMine()}
async function loadPosts(){let ps=await api('/api/posts'),f=document.getElementById('feed');f.innerHTML='';ps.forEach(p=>{let c=document.createElement('div');c.className='card';c.innerHTML=`<div class="post-head"><div class="av ${p.avatar_class}">${p.avatar}</div><div><div class="user">${p.username}</div><div class="time">${p.created_at}</div></div><div class="more">•••</div></div><div class="row"><div class="qmain"><div class="question">${p.question}</div><div class="badge ${p.match_type==='green'?'green':''}">${p.match_type==='green'?'◎':'♡'} ${p.match_text}</div></div>${p.image_type==='laptop'?'<div class="thumb">:(</div>':''}</div><div class="meta"><div>💡 <b>${p.comment_count+12} öneri</b></div><button onclick="openComments(${p.id})">💬 <b>${p.comment_count} yorum</b></button></div>`;f.appendChild(c)})}
async function newPost(full){let i=document.getElementById(full?'fullAsk':'quickAsk'),q=i.value.trim();if(!q)return;await api('/api/posts',{method:'POST',body:JSON.stringify({question:q})});i.value='';await loadPosts();show('home')}
async function openComments(id){currentPost=id;document.getElementById('overlay').classList.add('show');document.getElementById('sheet').classList.add('show');await loadComments()}
function closeComments(){document.getElementById('overlay').classList.remove('show');document.getElementById('sheet').classList.remove('show')}
async function loadComments(){let cs=await api(`/api/posts/${currentPost}/comments`),b=document.getElementById('comments');b.innerHTML=cs.length?'':'<div>Henüz yorum yok.</div>';cs.forEach(c=>b.innerHTML+=`<div class="comment"><div class="cav">${c.username[0].toUpperCase()}</div><div class="ctxt"><span class="cname">${c.username}</span>${c.body}</div></div>`)}
async function sendComment(){let i=document.getElementById('commentInput'),t=i.value.trim();if(!t)return;await api(`/api/posts/${currentPost}/comments`,{method:'POST',body:JSON.stringify({body:t})});i.value='';await loadComments();await loadPosts()}
async function loadMine(){let ps=await api('/api/posts?mine=1'),m=document.getElementById('mine');m.innerHTML=ps.length?ps.map(p=>`<div class="postline">${p.question}</div>`).join(''):'<div class="postline">Henüz paylaşımın yok.</div>'}
loadPosts()
</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj, code=200):
        raw=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=="/":
            raw=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw);return
        c=conn()
        if u.path=="/api/posts":
            mine=parse_qs(u.query).get("mine")
            q="""SELECT p.*,COUNT(c.id) comment_count FROM posts p LEFT JOIN comments c ON c.post_id=p.id"""
            if mine:q+=" WHERE p.username='aysuonerir'"
            q+=" GROUP BY p.id ORDER BY p.id DESC"
            self.send_json([dict(x) for x in c.execute(q).fetchall()]);c.close();return
        if u.path.startswith("/api/posts/") and u.path.endswith("/comments"):
            pid=int(u.path.split("/")[3]);rows=c.execute("SELECT * FROM comments WHERE post_id=? ORDER BY id",(pid,)).fetchall();self.send_json([dict(x) for x in rows]);c.close();return
        self.send_json({"error":"not found"},404);c.close()
    def do_POST(self):
        u=urlparse(self.path);length=int(self.headers.get("Content-Length","0"));data=json.loads(self.rfile.read(length) or b"{}");c=conn()
        if u.path=="/api/posts":
            q=(data.get("question") or "").strip()
            cur=c.execute("""INSERT INTO posts(username,avatar,avatar_class,question,match_text,match_type,image_type,created_at)
            VALUES(?,?,?,?,?,?,?,?)""",("aysuonerir","A","",q,"Zevk profiline göre eşleşmeler hazırlanıyor","blue","","şimdi"));c.commit();self.send_json({"id":cur.lastrowid},201);c.close();return
        if u.path.startswith("/api/posts/") and u.path.endswith("/comments"):
            pid=int(u.path.split("/")[3]);body=(data.get("body") or "").strip()
            cur=c.execute("INSERT INTO comments(post_id,username,body,created_at) VALUES(?,?,?,?)",(pid,"sen",body,"şimdi"));c.commit();self.send_json({"id":cur.lastrowid},201);c.close();return
        self.send_json({"error":"not found"},404);c.close()

if __name__=="__main__":
    port=int(os.environ.get("PORT","8000"))
    print(f"Ne Önerirsin? -> http://127.0.0.1:{port}")
    ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()
