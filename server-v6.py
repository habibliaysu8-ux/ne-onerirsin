
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
import sqlite3, json, os, re

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "demo.db"
MAX_UPLOAD = 6 * 1024 * 1024
APP_VERSION = 'v6-comment-edit-delete-20260818'

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def columns(c, table):
    return {r["name"] for r in c.execute(f"PRAGMA table_info({table})").fetchall()}

def add_column(c, table, name, definition):
    if name not in columns(c, table):
        c.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

def init_db():
    c = db()
    cur = c.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS posts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL DEFAULT 'aysuonerir',
      avatar TEXT NOT NULL DEFAULT 'A',
      avatar_class TEXT DEFAULT '',
      question TEXT,
      text TEXT,
      post_type TEXT DEFAULT 'question',
      match_text TEXT DEFAULT '',
      match_type TEXT DEFAULT 'blue',
      created_at TEXT DEFAULT 'şimdi',
      image BLOB,
      image_mime TEXT
    );
    CREATE TABLE IF NOT EXISTS comments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      post_id INTEGER NOT NULL,
      username TEXT NOT NULL,
      body TEXT NOT NULL,
      created_at TEXT DEFAULT 'şimdi'
    );
    CREATE TABLE IF NOT EXISTS profile(
      id INTEGER PRIMARY KEY CHECK(id=1),
      name TEXT NOT NULL DEFAULT 'Aysu',
      handle TEXT NOT NULL DEFAULT '@aysuonerir',
      bio TEXT NOT NULL DEFAULT '',
      image BLOB,
      image_mime TEXT
    );
    CREATE TABLE IF NOT EXISTS recs(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      note TEXT DEFAULT '',
      tag TEXT DEFAULT '',
      link TEXT DEFAULT '',
      image BLOB,
      image_mime TEXT,
      created_at TEXT DEFAULT 'şimdi'
    );
    """)

    add_column(c, "posts", "text", "TEXT")
    add_column(c, "posts", "post_type", "TEXT DEFAULT 'question'")
    add_column(c, "posts", "image", "BLOB")
    add_column(c, "posts", "image_mime", "TEXT")
    add_column(c, "profile", "image", "BLOB")
    add_column(c, "profile", "image_mime", "TEXT")

    if "question" in columns(c, "posts"):
        c.execute("UPDATE posts SET text=question WHERE (text IS NULL OR text='') AND question IS NOT NULL")
    c.execute("UPDATE posts SET post_type='question' WHERE post_type IS NULL OR post_type=''")

    if cur.execute("SELECT COUNT(*) FROM profile").fetchone()[0] == 0:
        cur.execute("INSERT INTO profile(id,name,handle,bio) VALUES(1,?,?,?)",
                    ("Aysu","@aysuonerir","Kahve, psikoloji kitapları, sakin mekanlar ve minimal yaşam seviyorum."))

    if cur.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO posts(username,avatar,avatar_class,text,post_type,match_text,match_type,created_at)
        VALUES(?,?,?,?,?,?,?,?)
        """,[
          ("melis.oztrk","M","","İsteme makyajı için nereyi önerirsiniz?","question","Seninle %88 uyumlu","blue","2 saat önce"),
          ("emirhan.tr","E","e","Psikoloji kitabı arıyorum, ne önerirsiniz?","question","Ortak zevk: kitap, sakin mekanlar","green","4 saat önce"),
          ("aysuonerir","A","","İnsan Olmak kitabını öneriyorum; yeni başlayanlar için çok akıcı.","recommendation","Seninle %91 uyumlu","blue","5 saat önce")
        ])
        cur.executemany("INSERT INTO comments(post_id,username,body,created_at) VALUES(?,?,?,?)",[
          (1,"ece.makeup","Doğal görünüm istiyorsan prova makyajı mutlaka iste.","1 saat önce"),
          (1,"selin","Kadıköy tarafında güzel bir yer vardı, adını yazabilirim.","45 dk önce"),
          (2,"kitapkurdu","İnsan Olmak ile başlayabilirsin.","2 saat önce")
        ])

    if cur.execute("SELECT COUNT(*) FROM recs").fetchone()[0] == 0:
        cur.executemany("INSERT INTO recs(title,note,tag,created_at) VALUES(?,?,?,?)",[
          ("İnsan Olmak – Engin Geçtan","Şu an okuyorum, çok iyi.","Kitap","dün"),
          ("Minoa","Kahvesi ve ortamı çok iyi.","Mekan","2 gün önce")
        ])

    c.commit()
    c.close()

init_db()

HTML = r"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Ne Önerirsin?</title>
<style>
:root{--bg:#f5f7fb;--card:#fff;--line:#e7ebf2;--text:#15203f;--muted:#7a8498;--blue:#3b63f0;--blue-soft:#edf3ff;--green:#eaf7ef;--green-text:#3e8259;--footer:66px}
*{box-sizing:border-box;min-width:0}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;background:var(--bg);overflow-x:hidden}
body{margin:0;width:100%;min-height:100dvh;overflow-x:hidden;background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:var(--text)}
button,input,textarea,select{font-family:inherit;font-size:16px}button{touch-action:manipulation}img{max-width:100%;height:auto}
.app{width:min(100%,430px);max-width:100%;min-height:100svh;margin:0 auto;background:var(--bg);position:relative;overflow-x:hidden}.screen{width:100%;max-width:100%;overflow-x:hidden}
.screen{display:none}.screen.active{display:block}
.header{position:sticky;top:0;z-index:15;width:100%;padding:12px 14px;background:rgba(255,255,255,.97);border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;backdrop-filter:blur(12px)}
.brand{display:flex;align-items:center;gap:9px;overflow:hidden}.logo{width:32px;height:32px;flex:0 0 32px;border-radius:10px;background:linear-gradient(135deg,#3b63f0,#7895ff);display:grid;place-items:center;color:#fff;font-weight:900}.brand h1{margin:0;font-size:19px;line-height:1.1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.head-avatar{width:34px;height:34px;border-radius:50%;background:#eef1f7;display:grid;place-items:center;overflow:hidden;font-weight:800;flex:0 0 34px;border:0}.head-avatar img{width:100%;height:100%;object-fit:cover}
.content{width:100%;padding:11px 11px calc(var(--footer) + 24px + env(safe-area-inset-bottom))}
.panel,.card,.profile-card{width:100%;background:#fff;border:1px solid var(--line);border-radius:17px}.panel{padding:13px}.title{font-size:15px;font-weight:850}.desc{font-size:12px;color:var(--muted);margin-top:5px;line-height:1.35}
.primary{width:100%;border:0;border-radius:13px;background:var(--blue);color:#fff;font-weight:800;padding:11px 12px;margin-top:10px}
.filters{display:flex;gap:7px;overflow-x:auto;padding:11px 1px 7px;scrollbar-width:none}.filters::-webkit-scrollbar{display:none}.chip{flex:0 0 auto;border:1px solid #dde2eb;border-radius:999px;background:#fff;padding:7px 11px;font-size:12px}.chip.active{background:var(--blue);border-color:var(--blue);color:#fff}
.section{display:flex;align-items:center;justify-content:space-between;margin:11px 2px 8px}.section h2{margin:0;font-size:17px;line-height:1.2}.link{font-size:12px;color:var(--blue);font-weight:800}
.feed{display:grid;gap:8px}.card{padding:11px;overflow:hidden}.post-head{display:flex;align-items:center;gap:9px}.av{width:35px;height:35px;flex:0 0 35px;border-radius:50%;display:grid;place-items:center;color:#fff;font-size:13px;font-weight:900;background:linear-gradient(135deg,#d98fbf,#8e63ce);overflow:hidden}.av.e{background:linear-gradient(135deg,#64a6f5,#4e87e4)}.av.b{background:linear-gradient(135deg,#69cf9b,#78c848)}.av img{width:100%;height:100%;object-fit:cover}
.post-info{min-width:0;flex:1}.ptype{font-size:9px;color:var(--blue);font-weight:900;text-transform:uppercase;letter-spacing:.6px}.user{font-size:13px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.time{font-size:10.5px;color:var(--muted);margin-top:1px}.more{color:#a0a8b8;flex:0 0 auto}.post-text{font-size:14.5px;line-height:1.34;margin:9px 0 7px;overflow-wrap:anywhere}
.post-photo{display:block;width:100%;max-height:310px;object-fit:cover;border-radius:13px;margin:8px 0}.badge{display:inline-flex;max-width:100%;padding:5px 8px;border-radius:999px;background:var(--blue-soft);color:var(--blue);font-size:11px;font-weight:800;white-space:normal;line-height:1.2}.badge.green{background:var(--green);color:var(--green-text)}
.meta{margin-top:9px;font-size:12px;color:#687286}.meta button{border:0;background:transparent;color:inherit;padding:3px 0;font-weight:700}
.people{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.person{background:#fff;border:1px solid var(--line);border-radius:14px;padding:9px 5px;text-align:center;overflow:hidden}.person .av{margin:0 auto;width:32px;height:32px}.person-name{font-size:10.5px;font-weight:850;margin-top:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.person-match{font-size:9.5px;color:var(--blue);font-weight:800;margin-top:2px}
.footer{position:fixed;z-index:20;left:50%;bottom:0;transform:translateX(-50%);width:100%;max-width:430px;height:calc(var(--footer) + env(safe-area-inset-bottom));padding-bottom:env(safe-area-inset-bottom);background:#fff;border-top:1px solid var(--line);display:grid;grid-template-columns:repeat(3,1fr)}.nav{border:0;background:transparent;color:#7b8497;font-size:10.5px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px}.nav.active{color:var(--blue);font-weight:800}.nav-icon{font-size:19px;line-height:1}.nav.main .nav-icon{width:40px;height:40px;border-radius:50%;background:var(--blue);color:#fff;display:grid;place-items:center;font-size:27px;box-shadow:0 6px 16px rgba(59,99,240,.25)}
.choice{display:grid;grid-template-columns:1fr 1fr;gap:8px}.mode{border:1px solid var(--line);border-radius:14px;background:#fff;padding:11px 7px;font-weight:850;color:var(--text)}.mode.active{border:2px solid var(--blue);background:#f8faff;color:var(--blue)}.mode small{display:block;font-size:10px;color:var(--muted);font-weight:500;margin-top:3px}
.label{font-size:11.5px;color:var(--muted);font-weight:700;margin:12px 1px 5px}.textarea,.input{width:100%;border:1px solid #dce2ec;border-radius:13px;background:#fff;color:var(--text);font-size:16px;padding:11px 12px;outline:none}.textarea{min-height:102px;resize:none}.textarea:focus,.input:focus{border-color:#9bb4ff;box-shadow:0 0 0 3px #eef3ff}
.file-input{position:absolute;opacity:0;pointer-events:none;width:1px;height:1px}.photo-actions{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:7px}.photo-actions .photo-button{margin-top:0;text-align:center}
.photo-button{display:block;width:100%;border:1px dashed #cbd3e1;border-radius:13px;background:#fafbfc;padding:12px;text-align:center;font-size:13px;font-weight:800;color:#4c5870}.preview-wrap{display:none;position:relative;margin-top:8px}.preview-wrap.show{display:block}.preview{display:block;width:100%;max-height:260px;object-fit:cover;border-radius:13px}.remove-photo{position:absolute;right:8px;top:8px;width:30px;height:30px;border:0;border-radius:50%;background:rgba(16,24,40,.78);color:#fff;font-weight:900}
.profile-card{padding:13px;display:flex;gap:11px}.profile-pic{width:72px;height:72px;flex:0 0 72px;border-radius:50%;background:linear-gradient(135deg,#ff9d68,#8d5ed1);display:grid;place-items:center;color:#fff;font-size:23px;font-weight:900;overflow:hidden}.profile-pic img{width:100%;height:100%;object-fit:cover}.profile-name{font-size:20px;font-weight:900}.handle2{font-size:12px;color:var(--blue);font-weight:800}.bio{font-size:11.5px;color:#596379;line-height:1.35;margin-top:5px}.tags{display:flex;gap:6px;flex-wrap:wrap}.tag{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 8px;font-size:10.5px}.recs{display:grid;gap:7px}.rec{background:#fff;border:1px solid var(--line);border-radius:14px;padding:9px;display:flex;gap:9px}.rec-img{width:64px;height:64px;flex:0 0 64px;border-radius:11px;background:#f3f5f8;display:grid;place-items:center;overflow:hidden}.rec-img img{width:100%;height:100%;object-fit:cover}.rec-tag{font-size:9.5px;color:var(--blue);font-weight:900}.rec-title{font-size:12.5px;font-weight:900;margin-top:2px}.rec-note{font-size:10.5px;color:var(--muted);line-height:1.3;margin-top:3px}
.overlay{position:fixed;inset:0;z-index:40;background:rgba(15,23,42,.28);display:none}.overlay.show{display:block}.sheet{position:fixed;z-index:41;left:50%;bottom:-110%;transform:translateX(-50%);width:100%;max-width:430px;max-height:min(68dvh,520px);background:#fff;border-radius:21px 21px 0 0;display:flex;flex-direction:column;transition:bottom .22s ease;overflow:hidden}.sheet.show{bottom:0}.drag{width:50px;height:5px;border-radius:999px;background:#d7dce6;margin:9px auto}.sheet-title{padding:2px 14px 10px;font-size:16px;font-weight:900;border-bottom:1px solid var(--line)}.comments{flex:1;min-height:0;overflow-y:auto;padding:10px 11px;display:grid;gap:8px;-webkit-overflow-scrolling:touch}.comment{display:flex;gap:8px;align-items:flex-start}.cav{width:30px;height:30px;flex:0 0 30px;border-radius:50%;background:#cd75a7;color:#fff;display:grid;place-items:center;font-size:11px;font-weight:900}.comment-body{display:flex;align-items:flex-start;gap:4px;min-width:0;flex:1}.ctext{background:#f7f9fc;border-radius:13px;padding:8px 9px;font-size:12.5px;line-height:1.32;overflow-wrap:anywhere;min-width:0;flex:1}.cname{display:block;font-weight:900}.comment-more{width:25px;height:25px;flex:0 0 25px;border:0;border-radius:50%;background:transparent;color:#9aa3b4;font-size:17px;line-height:1;display:grid;place-items:center;padding:0}.comment-more:active{background:#eef1f6}.comment-actions{display:none;gap:5px;margin-top:5px}.comment-actions.show{display:flex}.comment-action{border:1px solid #dce2ec;border-radius:9px;background:#fff;color:#536078;font-size:10.5px;font-weight:800;padding:5px 7px}.comment-action.danger{color:#c63b4a}.comment-form{flex:0 0 auto;display:flex;gap:7px;padding:9px 10px calc(9px + env(safe-area-inset-bottom));border-top:1px solid var(--line);background:#fff}.comment-form input{flex:1;border:1px solid #dce2ec;border-radius:12px;padding:10px;font-size:16px;min-width:0;max-width:100%}.comment-form button{border:0;border-radius:12px;background:var(--blue);color:#fff;font-weight:800;padding:0 12px}

@supports (-webkit-touch-callout:none){
  input,textarea,select{font-size:16px!important}
}
@media(max-width:350px){.brand h1{font-size:17px}.post-text{font-size:13.5px}.choice{grid-template-columns:1fr}.people{gap:5px}}
</style>
</head>
<body>
<div class="app" data-build="v6-comment-edit-delete">

<section id="home" class="screen active">
  <div class="header">
    <div class="brand"><div class="logo">N</div><h1>Ne Önerirsin?</h1></div>
    <div class="head-avatar" id="topAvatar">A</div>
  </div>
  <div class="content">
    <div class="panel">
      <div class="title">Bir şey sor ya da öner</div>
      <div class="desc">Yazı yazabilir, istersen fotoğraf da ekleyebilirsin.</div>
      <button class="primary" onclick="showScreen('create')">Paylaş</button>
    </div>
    <div class="filters"><button class="chip active">Tümü</button><button class="chip">Sorular</button><button class="chip">Öneriler</button><button class="chip">Yeni</button></div>
    <div class="section"><h2>Akış</h2></div>
    <div id="feed" class="feed"></div>
    <div class="section"><h2>Benim Gibiler</h2><span class="link">Tümünü gör</span></div>
    <div class="people">
      <div class="person"><div class="av">S</div><div class="person-name">sude.aksoy</div><div class="person-match">%92 uyum</div></div>
      <div class="person"><div class="av e">K</div><div class="person-name">kaan.yldz</div><div class="person-match">%87 uyum</div></div>
      <div class="person"><div class="av b">D</div><div class="person-name">dilara.m</div><div class="person-match">%84 uyum</div></div>
    </div>
  </div>
</section>

<section id="create" class="screen">
  <div class="header"><div class="brand"><div class="logo">N</div><h1>Paylaş</h1></div><button class="head-avatar" onclick="showScreen('home')">×</button></div>
  <div class="content">
    <div class="panel">
      <div class="choice">
        <button id="questionMode" class="mode active" onclick="selectMode('question')">❓ Soru Sor<small>Topluluktan yardım iste</small></button>
        <button id="recMode" class="mode" onclick="selectMode('recommendation')">★ Öneri Paylaş<small>Sevdiğin bir şeyi öner</small></button>
      </div>
      <div class="label" id="postLabel">Sorunu yaz</div>
      <textarea id="postText" class="textarea" placeholder="Örn. Gömleğimde bu leke var, nasıl çıkarabilirim?"></textarea>
      <div class="label">Fotoğraf (isteğe bağlı)</div>
      <input id="postImage" class="file-input" type="file" accept="image/*">
      <input id="postCamera" class="file-input" type="file" accept="image/*" capture="environment">
      <div class="photo-actions">
        <label for="postCamera" class="photo-button">📷 Fotoğraf çek</label>
        <label for="postImage" class="photo-button">🖼️ Galeriden seç</label>
      </div>
      <div id="postPreviewWrap" class="preview-wrap"><img id="postPreview" class="preview" alt=""><button class="remove-photo" onclick="clearPostPhoto()" type="button">×</button></div>
      <button class="primary" onclick="createPost()">Paylaş</button>
    </div>
  </div>
</section>

<section id="profile" class="screen">
  <div class="header"><div class="brand"><div class="logo">N</div><h1>Profil</h1></div></div>
  <div class="content">
    <div class="profile-card"><label for="profileImage" style="position:relative;display:block;flex:0 0 72px;cursor:pointer"><div class="profile-pic" id="profilePic">A</div><span style="position:absolute;right:-2px;bottom:-2px;width:26px;height:26px;border-radius:50%;background:#3b63f0;color:white;display:grid;place-items:center;border:2px solid white;font-size:13px">📷</span></label><div><div class="profile-name">Aysu</div><div class="handle2">@aysuonerir</div><div class="bio">Kahve, psikoloji kitapları, sakin mekanlar ve minimal yaşam seviyorum.</div></div></div>
    <input id="profileImage" class="file-input" type="file" accept="image/*">
    <input id="profileCamera" class="file-input" type="file" accept="image/*" capture="user">
    <div class="photo-actions" style="margin-top:8px">
      <label for="profileCamera" class="photo-button">📷 Fotoğraf çek</label>
      <label for="profileImage" class="photo-button">🖼️ Galeriden seç</label>
    </div>
    <div class="section"><h2>Zevklerim & Hobilerim</h2></div>
    <div class="tags"><span class="tag">♫ Alternatif</span><span class="tag">☕ Filtre kahve</span><span class="tag">📚 Psikoloji</span><span class="tag">🎬 Bağımsız film</span><span class="tag">🎨 Resim</span></div>
    <div class="section"><h2>Benim Önerilerim</h2><span class="link" onclick="selectMode('recommendation');showScreen('create')">+ Yeni Öneri</span></div>
    <div id="recs" class="recs"></div>
  </div>
</section>

<nav class="footer">
  <button class="nav active" data-screen="home" onclick="showScreen('home',this)"><span class="nav-icon">⌂</span><span>Ana Sayfa</span></button>
  <button class="nav main" data-screen="create" onclick="showScreen('create',this)"><span class="nav-icon">+</span><span>Paylaş</span></button>
  <button class="nav" data-screen="profile" onclick="showScreen('profile',this)"><span class="nav-icon">◎</span><span>Profil</span></button>
</nav>
</div>

<div id="overlay" class="overlay" onclick="closeComments()"></div>
<div id="sheet" class="sheet">
  <div class="drag"></div><div class="sheet-title">Yanıtlar</div><div id="comments" class="comments"></div>
  <div class="comment-form"><input id="commentInput" placeholder="Yanıtını yaz..." autocomplete="off"><button onclick="sendComment()">Gönder</button></div>
</div>

<script>
let currentPost=null, postMode='question';

async function api(url,options={}){
  const r=await fetch(url,options);
  if(!r.ok) throw new Error(await r.text());
  const ct=r.headers.get('content-type')||'';
  return ct.includes('application/json')?r.json():r.text();
}
function esc(v){return String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function showScreen(id,btn){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  document.querySelectorAll('.nav').forEach(n=>n.classList.remove('active'));
  const n=btn||document.querySelector(`.nav[data-screen="${id}"]`);
  if(n)n.classList.add('active');
  if(id==='profile'){loadRecs();loadProfilePhoto();}
  window.scrollTo(0,0);
}
function selectMode(mode){
  postMode=mode;
  document.getElementById('questionMode').classList.toggle('active',mode==='question');
  document.getElementById('recMode').classList.toggle('active',mode==='recommendation');
  document.getElementById('postLabel').textContent=mode==='question'?'Sorunu yaz':'Önerini yaz';
  document.getElementById('postText').placeholder=mode==='question'?'Örn. Gömleğimde bu leke var, nasıl çıkarabilirim?':'Örn. Bu kitabı öneriyorum; çok akıcı ve güzel.';
}
let selectedPostFile=null;
function previewPostFile(f){
  if(!f){return;}
  if(!f.type.startsWith('image/')){alert('Lütfen bir fotoğraf seç.');clearPostPhoto();return;}
  selectedPostFile=f;
  document.getElementById('postPreview').src=URL.createObjectURL(f);
  document.getElementById('postPreviewWrap').classList.add('show');
}
document.getElementById('postImage').addEventListener('change',e=>previewPostFile(e.target.files[0]));
document.getElementById('postCamera').addEventListener('change',e=>previewPostFile(e.target.files[0]));
function clearPostPhoto(){
  selectedPostFile=null;
  document.getElementById('postImage').value='';
  document.getElementById('postCamera').value='';
  document.getElementById('postPreview').removeAttribute('src');
  document.getElementById('postPreviewWrap').classList.remove('show');
}
async function loadPosts(){
  const data=await api('/api/posts'),feed=document.getElementById('feed');
  feed.innerHTML='';
  data.forEach(p=>{
    const card=document.createElement('article');card.className='card';
    const av=p.username==='aysuonerir'?`<img src="/media/profile?v=${Date.now()}" onerror="this.remove();this.parentElement.textContent='A'">`:esc(p.avatar);
    card.innerHTML=`<div class="post-head"><div class="av ${esc(p.avatar_class||'')}">${av}</div><div class="post-info"><div class="ptype">${p.post_type==='recommendation'?'Öneri':'Soru'}</div><div class="user">${esc(p.username)}</div><div class="time">${esc(p.created_at)}</div></div><div class="more">•••</div></div><div class="post-text">${esc(p.text)}</div>${p.has_image?`<img class="post-photo" src="/media/post/${p.id}?v=${Date.now()}" alt="Paylaşım fotoğrafı">`:''}<div class="badge ${p.match_type==='green'?'green':''}">${p.match_type==='green'?'◎':'♡'} ${esc(p.match_text)}</div><div class="meta"><button onclick="openComments(${p.id})">💬 ${p.comment_count} yanıt</button></div>`;
    feed.appendChild(card);
  });
}
async function createPost(){
  const text=document.getElementById('postText').value.trim();if(!text)return;
  const fd=new FormData();fd.append('post_type',postMode);fd.append('text',text);
  const f=selectedPostFile;if(f)fd.append('image',f);
  await api('/api/posts',{method:'POST',body:fd});
  document.getElementById('postText').value='';clearPostPhoto();await loadPosts();showScreen('home');
}
async function openComments(id){currentPost=id;document.getElementById('overlay').classList.add('show');document.getElementById('sheet').classList.add('show');await loadComments();resizeSheet()}
function closeComments(){document.getElementById('overlay').classList.remove('show');const s=document.getElementById('sheet');s.classList.remove('show');s.style.bottom='';document.getElementById('commentInput').blur()}
async function loadComments(){
  const data=await api(`/api/posts/${currentPost}/comments`),box=document.getElementById('comments');box.innerHTML='';
  if(!data.length){box.innerHTML='<div style="font-size:12px;color:#7a8498">Henüz yanıt yok. İlk yanıtı sen yaz.</div>';return;}
  data.forEach(c=>{
    const mine=c.username==='sen';
    box.innerHTML+=`<div class="comment" id="comment-${c.id}"><div class="cav">${esc(c.username[0].toUpperCase())}</div><div class="comment-body"><div class="ctext"><span class="cname">${esc(c.username)}</span><span id="comment-text-${c.id}">${esc(c.body)}</span>${mine?`<div class="comment-actions" id="comment-actions-${c.id}"><button class="comment-action" onclick="editComment(${c.id})">Düzenle</button><button class="comment-action danger" onclick="deleteComment(${c.id})">Sil</button></div>`:''}</div>${mine?`<button class="comment-more" aria-label="Yorum seçenekleri" onclick="toggleCommentActions(${c.id})">⋯</button>`:''}</div></div>`;
  });
}
function toggleCommentActions(id){
  document.querySelectorAll('.comment-actions').forEach(el=>{if(el.id!==`comment-actions-${id}`)el.classList.remove('show')});
  document.getElementById(`comment-actions-${id}`)?.classList.toggle('show');
}
async function editComment(id){
  const el=document.getElementById(`comment-text-${id}`);if(!el)return;
  const body=prompt('Yorumunu düzenle:',el.textContent);
  if(body===null)return;
  const clean=body.trim();if(!clean){alert('Yorum boş bırakılamaz.');return;}
  await api(`/api/comments/${id}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({body:clean})});
  await loadComments();
}
async function deleteComment(id){
  if(!confirm('Bu yorumu silmek istiyor musun?'))return;
  await api(`/api/comments/${id}`,{method:'DELETE'});
  await loadComments();await loadPosts();
}
async function sendComment(){
  const i=document.getElementById('commentInput'),body=i.value.trim();if(!body)return;
  await api(`/api/posts/${currentPost}/comments`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({body})});
  i.value='';await loadComments();await loadPosts();
}
async function uploadProfilePhoto(f,input){
  if(!f)return;
  if(!f.type.startsWith('image/')){alert('Lütfen bir fotoğraf seç.');if(input)input.value='';return;}
  const local=URL.createObjectURL(f);
  document.getElementById('profilePic').innerHTML=`<img src="${local}" alt="Profil fotoğrafı">`;
  try{
    const fd=new FormData();fd.append('image',f);await api('/api/profile/photo',{method:'POST',body:fd});loadProfilePhoto();await loadPosts();
  }catch(err){alert('Profil fotoğrafı yüklenemedi.');loadProfilePhoto();}
  if(input)input.value='';
}
document.getElementById('profileImage').addEventListener('change',e=>uploadProfilePhoto(e.target.files[0],e.target));
document.getElementById('profileCamera').addEventListener('change',e=>uploadProfilePhoto(e.target.files[0],e.target));
function loadProfilePhoto(){
  const v=Date.now();
  document.getElementById('profilePic').innerHTML=`<img src="/media/profile?v=${v}" onerror="this.remove();this.parentElement.textContent='A'">`;
  document.getElementById('topAvatar').innerHTML=`<img src="/media/profile?v=${v}" onerror="this.remove();this.parentElement.textContent='A'">`;
}
async function loadRecs(){
  const data=await api('/api/recs'),box=document.getElementById('recs');box.innerHTML='';
  data.forEach(r=>box.innerHTML+=`<div class="rec"><div class="rec-img">${r.has_image?`<img src="/media/rec/${r.id}?v=${Date.now()}">`:'★'}</div><div><div class="rec-tag">${esc(r.tag||'Öneri')}</div><div class="rec-title">${esc(r.title)}</div><div class="rec-note">${esc(r.note)}</div></div></div>`);
}
function resizeSheet(){
  const sheet=document.getElementById('sheet');
  if(!window.visualViewport){sheet.style.bottom='0px';return;}
  const vv=window.visualViewport;
  const keyboard=Math.max(0,window.innerHeight-(vv.height+vv.offsetTop));
  sheet.style.maxHeight=Math.min(vv.height*.72,520)+'px';
  if(sheet.classList.contains('show')) sheet.style.bottom=keyboard+'px';
}
if(window.visualViewport){visualViewport.addEventListener('resize',resizeSheet);visualViewport.addEventListener('scroll',resizeSheet)}
selectMode('question');loadPosts();loadProfilePhoto();
</script>
</body></html>"""

def parse_multipart(handler):
    content_type=handler.headers.get("Content-Type","")
    length=int(handler.headers.get("Content-Length","0") or "0")
    if length>MAX_UPLOAD+2*1024*1024:
        raise ValueError("Dosya çok büyük")
    body=handler.rfile.read(length)
    raw=b"Content-Type: "+content_type.encode()+b"\r\nMIME-Version: 1.0\r\n\r\n"+body
    msg=BytesParser(policy=default).parsebytes(raw)
    fields,files={},{}
    if not msg.is_multipart():
        return fields,files
    for part in msg.iter_parts():
        name=part.get_param("name",header="content-disposition")
        if not name: continue
        data=part.get_payload(decode=True) or b""
        filename=part.get_filename()
        if filename:
            if len(data)>MAX_UPLOAD: raise ValueError("Fotoğraf 6 MB'dan küçük olmalı")
            files[name]=(filename,data,part.get_content_type())
        else:
            fields[name]=data.decode(part.get_content_charset() or "utf-8",errors="replace")
    return fields,files

class Handler(BaseHTTPRequestHandler):
    def send_json(self,obj,code=200):
        raw=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(raw)
    def send_bytes(self,data,mime):
        if not data:self.send_response(404);self.end_headers();return
        self.send_response(200);self.send_header("Content-Type",mime or "application/octet-stream");self.send_header("Content-Length",str(len(data)));self.send_header("Cache-Control","no-store");self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/":
            raw=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Content-Length",str(len(raw)));self.send_header("Cache-Control","no-store, no-cache, must-revalidate");self.end_headers();self.wfile.write(raw);return
        if path=="/version":
            return self.send_json({"version":APP_VERSION})
        c=db()
        if path=="/api/posts":
            rows=c.execute("""SELECT p.id,p.username,p.avatar,p.avatar_class,p.post_type,COALESCE(NULLIF(p.text,''),p.question,'') text,p.match_text,p.match_type,p.created_at,CASE WHEN p.image IS NULL THEN 0 ELSE 1 END has_image,COUNT(cm.id) comment_count FROM posts p LEFT JOIN comments cm ON cm.post_id=p.id GROUP BY p.id ORDER BY p.id DESC""").fetchall()
            c.close();return self.send_json([dict(r) for r in rows])
        m=re.fullmatch(r"/api/posts/(\d+)/comments",path)
        if m:
            rows=c.execute("SELECT * FROM comments WHERE post_id=? ORDER BY id",(int(m.group(1)),)).fetchall();c.close();return self.send_json([dict(r) for r in rows])
        m=re.fullmatch(r"/media/post/(\d+)",path)
        if m:
            r=c.execute("SELECT image,image_mime FROM posts WHERE id=?",(int(m.group(1)),)).fetchone();c.close();return self.send_bytes(r["image"] if r else None,r["image_mime"] if r else None)
        if path=="/media/profile":
            r=c.execute("SELECT image,image_mime FROM profile WHERE id=1").fetchone();c.close();return self.send_bytes(r["image"] if r else None,r["image_mime"] if r else None)
        if path=="/api/recs":
            rows=c.execute("SELECT id,title,note,tag,link,created_at,CASE WHEN image IS NULL THEN 0 ELSE 1 END has_image FROM recs ORDER BY id DESC").fetchall();c.close();return self.send_json([dict(r) for r in rows])
        m=re.fullmatch(r"/media/rec/(\d+)",path)
        if m:
            r=c.execute("SELECT image,image_mime FROM recs WHERE id=?",(int(m.group(1)),)).fetchone();c.close();return self.send_bytes(r["image"] if r else None,r["image_mime"] if r else None)
        c.close();return self.send_json({"error":"not found"},404)
    def do_POST(self):
        path=urlparse(self.path).path;c=db()
        if path=="/api/posts":
            try:fields,files=parse_multipart(self)
            except ValueError as e:c.close();return self.send_json({"error":str(e)},413)
            text=(fields.get("text") or "").strip();post_type=(fields.get("post_type") or "question").strip()
            if not text:c.close();return self.send_json({"error":"text required"},400)
            image=files.get("image")
            if image and not (image[2] or "").startswith("image/"):
                c.close();return self.send_json({"error":"image required"},400)
            cur=c.execute("""INSERT INTO posts(username,avatar,avatar_class,text,post_type,match_text,match_type,created_at,image,image_mime) VALUES(?,?,?,?,?,?,?,?,?,?)""",("aysuonerir","A","",text,post_type,"Zevk profiline göre eşleşmeler hazırlanıyor","blue","şimdi",image[1] if image else None,image[2] if image else None))
            post_id=cur.lastrowid
            if post_type=="recommendation":
                c.execute("INSERT INTO recs(title,note,tag,created_at,image,image_mime) VALUES(?,?,?,?,?,?)",(text,"","Öneri","şimdi",image[1] if image else None,image[2] if image else None))
            c.commit();c.close();return self.send_json({"id":post_id},201)
        m=re.fullmatch(r"/api/posts/(\d+)/comments",path)
        if m:
            length=int(self.headers.get("Content-Length","0") or "0");data=json.loads(self.rfile.read(length) or b"{}");body=(data.get("body") or "").strip()
            if not body:c.close();return self.send_json({"error":"body required"},400)
            cur=c.execute("INSERT INTO comments(post_id,username,body,created_at) VALUES(?,?,?,?)",(int(m.group(1)),"sen",body,"şimdi"));c.commit();c.close();return self.send_json({"id":cur.lastrowid},201)
        if path=="/api/profile/photo":
            try:fields,files=parse_multipart(self)
            except ValueError as e:c.close();return self.send_json({"error":str(e)},413)
            image=files.get("image")
            if not image or not (image[2] or "").startswith("image/"):c.close();return self.send_json({"error":"image required"},400)
            c.execute("UPDATE profile SET image=?,image_mime=? WHERE id=1",(image[1],image[2]));c.commit();c.close();return self.send_json({"ok":True})
        c.close();return self.send_json({"error":"not found"},404)
    def do_PUT(self):
        path=urlparse(self.path).path;c=db()
        m=re.fullmatch(r"/api/comments/(\d+)",path)
        if m:
            comment_id=int(m.group(1))
            row=c.execute("SELECT username FROM comments WHERE id=?",(comment_id,)).fetchone()
            if not row:c.close();return self.send_json({"error":"comment not found"},404)
            if row["username"]!="sen":c.close();return self.send_json({"error":"forbidden"},403)
            length=int(self.headers.get("Content-Length","0") or "0")
            try:data=json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:c.close();return self.send_json({"error":"invalid json"},400)
            body=(data.get("body") or "").strip()
            if not body:c.close();return self.send_json({"error":"body required"},400)
            c.execute("UPDATE comments SET body=?,created_at=? WHERE id=?",(body,"düzenlendi",comment_id));c.commit();c.close();return self.send_json({"ok":True})
        c.close();return self.send_json({"error":"not found"},404)
    def do_DELETE(self):
        path=urlparse(self.path).path;c=db()
        m=re.fullmatch(r"/api/comments/(\d+)",path)
        if m:
            comment_id=int(m.group(1))
            row=c.execute("SELECT username FROM comments WHERE id=?",(comment_id,)).fetchone()
            if not row:c.close();return self.send_json({"error":"comment not found"},404)
            if row["username"]!="sen":c.close();return self.send_json({"error":"forbidden"},403)
            c.execute("DELETE FROM comments WHERE id=?",(comment_id,));c.commit();c.close();return self.send_json({"ok":True})
        c.close();return self.send_json({"error":"not found"},404)

if __name__=="__main__":
    port=int(os.environ.get("PORT","8000"))
    ThreadingHTTPServer(("0.0.0.0",port),Handler).serve_forever()
