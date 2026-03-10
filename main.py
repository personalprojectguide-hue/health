"""
Health  -- Meal plans, workouts, travel itineraries, and daily routines. Live better.

Setup:
  pip install -r requirements.txt
  cp .env.example .env          # add your GROQ_API_KEY
  uvicorn main:app --reload
  open http://localhost:8000
"""
import os, sqlite3, hashlib, secrets
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")
DB_FILE        = "health.db"
SYSTEM_PROMPTS = ["You are an expert Recipe from Ingredients assistant. List what's in your fridge. Get a delicious recipe with full instructions.", 'You are an expert Travel Itinerary Builder assistant. Tell us your destination, length, budget, and interests. Get a day-by-day itinerary.', 'You are an expert Meal Prep Planner assistant. Enter dietary preferences and number of people. Get a 7-day meal plan with a shopping list.', 'You are an expert Road Trip Planner assistant. Describe start, destination, and interests. Get a detailed road trip itinerary.', "You are an expert Date Night Planner assistant. Enter location, budget, and partner's interests. Get a personalised date night itinerary."]

app = FastAPI(title="Health ")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                email    TEXT UNIQUE NOT NULL,
                name     TEXT,
                password TEXT NOT NULL,
                token    TEXT UNIQUE,
                ts       TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS queries (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_idx INTEGER NOT NULL DEFAULT 0,
                prompt   TEXT NOT NULL,
                result   TEXT,
                ts       TEXT DEFAULT (datetime('now'))
            );
        """)
        conn.commit()

init_db()


# ── Frontend ──────────────────────────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Health </title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap" rel="stylesheet" />
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{--acc:#f5c842;--acc2:#ffd96a;--bg:#09080a;--s1:color-mix(in srgb,var(--bg) 60%,#111);--s2:color-mix(in srgb,var(--bg) 40%,#1a1a1a);--b1:rgba(255,255,255,.06);--b2:rgba(255,255,255,.11);--text:#e8eaef;--muted:#6b7280;--dim:#374151;--err:#f87171;--r:12px}
html,body{height:100%;font-family:"DM Sans",sans-serif;background:var(--bg);color:var(--text);overflow:hidden}
#auth-overlay{position:fixed;inset:0;z-index:200;background:var(--bg);display:none;align-items:center;justify-content:center;padding:24px}
.auth-box{width:100%;max-width:400px;background:var(--s1);border:1px solid var(--b2);border-radius:16px;padding:36px 32px}
.auth-logo{font-family:"Syne",sans-serif;font-size:22px;font-weight:800;color:var(--acc);margin-bottom:6px}
.auth-sub{color:var(--muted);font-size:13px;margin-bottom:20px}
.auth-tabs{display:flex;gap:0;margin-bottom:20px;background:var(--s2);border-radius:8px;padding:3px}
.auth-tab{flex:1;padding:8px;text-align:center;font-size:13px;font-weight:500;border-radius:6px;cursor:pointer;color:var(--muted)}
.auth-tab.active{background:var(--s1);color:var(--text)}
.auth-field{margin-bottom:14px}
.auth-field label{display:block;font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.auth-field input{width:100%;background:var(--s2);border:1px solid var(--b1);border-radius:8px;color:var(--text);padding:11px 14px;font-size:14px;font-family:"DM Sans",sans-serif;outline:none;transition:border-color .2s}
.auth-field input:focus{border-color:var(--acc)}
.auth-btn{width:100%;background:var(--acc);color:var(--bg);border:none;border-radius:8px;padding:12px;font-weight:700;font-size:14px;font-family:"DM Sans",sans-serif;cursor:pointer;margin-top:4px}
.auth-err{color:var(--err);font-size:12px;margin-top:10px;text-align:center}
#app{display:flex;height:100vh;overflow:hidden}
.sidebar{width:220px;flex-shrink:0;background:var(--s1);border-right:1px solid var(--b1);display:flex;flex-direction:column}
.sidebar-hdr{padding:18px 16px 14px;border-bottom:1px solid var(--b1)}
.sidebar-logo{font-family:"Syne",sans-serif;font-size:11px;color:var(--acc);letter-spacing:2px;margin-bottom:6px}
.suite-name{font-family:"Syne",sans-serif;font-size:15px;font-weight:700;line-height:1.2}
.suite-tag{font-size:11px;color:var(--muted);margin-top:3px}
.sidebar-nav{flex:1;padding:10px 8px;overflow-y:auto}
.nav-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:9px;cursor:pointer;transition:all .15s;font-size:13px;color:var(--muted);border:1px solid transparent;margin-bottom:2px}
.nav-item:hover{background:var(--s2);color:var(--text)}
.nav-item.active{background:color-mix(in srgb,var(--acc) 12%,transparent);border-color:color-mix(in srgb,var(--acc) 30%,transparent);color:var(--acc);font-weight:500}
.nav-dot{width:6px;height:6px;border-radius:50%;background:currentColor;flex-shrink:0;opacity:.5}
.nav-item.active .nav-dot{opacity:1}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{height:52px;flex-shrink:0;padding:0 24px;border-bottom:1px solid var(--b1);display:flex;align-items:center;justify-content:space-between}
.tool-title{font-family:"Syne",sans-serif;font-size:16px;font-weight:700}
.tool-tag{font-size:12px;color:var(--muted)}
.user-chip{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.user-avatar{width:26px;height:26px;border-radius:50%;background:var(--acc);color:var(--bg);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700}
.btn-logout{font-size:11px;color:var(--dim);cursor:pointer;background:none;border:1px solid var(--b1);border-radius:6px;padding:5px 10px;font-family:"DM Sans",sans-serif}
.content{flex:1;overflow-y:auto;padding:28px 32px;display:flex;gap:24px}
.tool-panel{display:none;width:100%;gap:24px}
.tool-panel.active{display:flex}
.form-col{flex:0 0 320px;display:flex;flex-direction:column;gap:14px}
.field{display:flex;flex-direction:column;gap:6px}
.field label{font-size:11px;font-weight:600;color:var(--muted);letter-spacing:.07em;text-transform:uppercase}
.field input,.field textarea,.field select{background:var(--s2);border:1px solid var(--b1);border-radius:var(--r);padding:12px 14px;color:var(--text);font-size:14px;font-family:"DM Sans",sans-serif;font-weight:300;outline:none;transition:border-color .2s;resize:vertical}
.field input:focus,.field textarea:focus,.field select:focus{border-color:var(--acc)}
.field textarea{min-height:90px}
.run-btn{background:var(--acc);color:var(--bg);font-weight:700;border:none;border-radius:var(--r);padding:13px 20px;cursor:pointer;font-size:14px;display:flex;align-items:center;gap:8px;transition:all .15s;font-family:"DM Sans",sans-serif;margin-top:4px}
.run-btn:disabled{opacity:.5;cursor:not-allowed}
.output-col{flex:1;display:flex;flex-direction:column;gap:12px;min-width:0}
.output-label{font-size:10px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--dim)}
.output-box{flex:1;background:var(--s1);border:1px solid var(--b1);border-radius:var(--r);padding:20px;font-size:13px;line-height:1.7;overflow-y:auto;min-height:200px;position:relative}
.output-empty{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--dim);gap:8px;pointer-events:none}
.output-empty .icon{font-size:28px;opacity:.4}
.copy-btn{align-self:flex-end;background:var(--s2);border:1px solid var(--b1);border-radius:8px;padding:6px 14px;color:var(--muted);font-size:12px;cursor:pointer;font-family:"DM Sans",sans-serif;display:none}
.copy-btn.visible{display:block}
.spinner{width:16px;height:16px;border:2px solid rgba(0,0,0,.3);border-top-color:#000;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
::-webkit-scrollbar{width:5px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--dim);border-radius:99px}
.output-box h1,.output-box h2,.output-box h3{font-family:"Syne",sans-serif;color:var(--acc);margin:12px 0 6px}
.output-box strong{color:var(--acc2)}
.output-box ul,.output-box ol{padding-left:20px}
.output-box li{margin-bottom:4px}
.output-box code{font-family:monospace;background:var(--s2);padding:2px 6px;border-radius:4px;font-size:12px}
</style>
</head>
<body>
<div id="auth-overlay">
  <div class="auth-box">
    <div class="auth-logo">⚡ DEPLO</div>
    <p class="auth-sub">Sign in to use Health </p>
    <div class="auth-tabs">
      <div class="auth-tab active" onclick="switchTab('login')">Sign in</div>
      <div class="auth-tab" onclick="switchTab('signup')">Sign up</div>
    </div>
    <div id="login-form">
      <div class="auth-field"><label>Email</label><input id="login-email" type="email" placeholder="you@example.com" /></div>
      <div class="auth-field"><label>Password</label><input id="login-password" type="password" placeholder="••••••••" /></div>
      <button class="auth-btn" onclick="doLogin()">Sign in</button>
      <div class="auth-err" id="login-err"></div>
    </div>
    <div id="signup-form" style="display:none">
      <div class="auth-field"><label>Name</label><input id="signup-name" type="text" placeholder="Your name" /></div>
      <div class="auth-field"><label>Email</label><input id="signup-email" type="email" placeholder="you@example.com" /></div>
      <div class="auth-field"><label>Password</label><input id="signup-password" type="password" placeholder="min 8 characters" /></div>
      <button class="auth-btn" onclick="doSignup()">Create account</button>
      <div class="auth-err" id="signup-err"></div>
    </div>
  </div>
</div>
<div id="app">
  <aside class="sidebar">
    <div class="sidebar-hdr">
      <div class="sidebar-logo">⚡ DEPLO</div>
      <div class="suite-name">Health </div>
      <div class="suite-tag">Meal plans, workouts, travel itineraries, and daily routines. Live better.</div>
    </div>
    <nav class="sidebar-nav" id="sidebar-nav"></nav>
  </aside>
  <div class="main">
    <div class="topbar">
      <div><div class="tool-title" id="topbar-title"></div><div class="tool-tag" id="topbar-tag"></div></div>
      <div class="user-chip" id="user-chip" style="display:none">
        <div class="user-avatar" id="user-avatar">?</div>
        <span id="user-name"></span>
        <button class="btn-logout" onclick="logout()">Logout</button>
      </div>
    </div>
    <div class="content" id="content"></div>
  </div>
</div>
<script>
const AUTH_ENABLED=true;
const TOOLS=[{"name": "Recipe from Ingredients", "tagline": "Cook something great with what you have", "promptTemplate": "Ingredients: {{ingredients}}\\nCuisine Style: {{cuisine_style}}\\nDietary Needs: {{dietary_needs}}\\nTime Available: {{time_available}}", "resultFormat": "steps", "inputs": [{"id": "ingredients", "label": "Ingredients", "type": "textarea", "placeholder": "Enter ingredients...", "required": true}, {"id": "cuisine_style", "label": "Cuisine Style", "type": "select", "options": ["Whatever works best", "Italian", "Asian", "Mexican", "Mediterranean", "American", "Indian"], "required": false}, {"id": "dietary_needs", "label": "Dietary Needs", "type": "select", "options": ["None", "Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Low carb"], "required": false}, {"id": "time_available", "label": "Time Available", "type": "select", "options": ["Whatever it takes", "Under 20 minutes", "Under 30 minutes", "Under 1 hour"], "required": false}]}, {"name": "Travel Itinerary Builder", "tagline": "Plan your perfect trip in minutes", "promptTemplate": "Destination: {{destination}}\\nDuration: {{duration}}\\nBudget: {{budget}}\\nInterests: {{interests}}", "resultFormat": "steps", "inputs": [{"id": "destination", "label": "Destination", "type": "textarea", "placeholder": "Enter destination...", "required": true}, {"id": "duration", "label": "Duration", "type": "text", "placeholder": "e.g. your duration", "required": false}, {"id": "budget", "label": "Budget", "type": "select", "options": ["Budget", "Mid-range", "Luxury", "No limit"], "required": false}, {"id": "interests", "label": "Interests", "type": "text", "placeholder": "e.g. your interests", "required": false}]}, {"name": "Meal Prep Planner", "tagline": "Plan your whole week of meals", "promptTemplate": "Dietary Needs: {{dietary_needs}}\\nPeople Count: {{people_count}}\\nCuisine Style: {{cuisine_style}}\\nBudget: {{budget}}", "resultFormat": "steps", "inputs": [{"id": "dietary_needs", "label": "Dietary Needs", "type": "select", "options": ["None", "Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "Low carb"], "required": true}, {"id": "people_count", "label": "People Count", "type": "select", "options": ["5", "10", "15", "20"], "required": false}, {"id": "cuisine_style", "label": "Cuisine Style", "type": "select", "options": ["Whatever works best", "Italian", "Asian", "Mexican", "Mediterranean", "American", "Indian"], "required": false}, {"id": "budget", "label": "Budget", "type": "select", "options": ["Budget", "Mid-range", "Luxury", "No limit"], "required": false}]}, {"name": "Road Trip Planner", "tagline": "Epic road trips, zero stress", "promptTemplate": "Start Location: {{start_location}}\\nEnd Destination: {{end_destination}}\\nDuration: {{duration}}\\nInterests: {{interests}}", "resultFormat": "steps", "inputs": [{"id": "start_location", "label": "Start Location", "type": "textarea", "placeholder": "Enter start location...", "required": true}, {"id": "end_destination", "label": "End Destination", "type": "text", "placeholder": "e.g. your end destination", "required": false}, {"id": "duration", "label": "Duration", "type": "text", "placeholder": "e.g. your duration", "required": false}, {"id": "interests", "label": "Interests", "type": "text", "placeholder": "e.g. your interests", "required": false}]}, {"name": "Date Night Planner", "tagline": "Plan the perfect evening out", "promptTemplate": "Location: {{location}}\\nBudget: {{budget}}\\nInterests: {{interests}}\\nOccasion: {{occasion}}", "resultFormat": "steps", "inputs": [{"id": "location", "label": "Location", "type": "textarea", "placeholder": "Enter location...", "required": true}, {"id": "budget", "label": "Budget", "type": "select", "options": ["Budget", "Mid-range", "Luxury", "No limit"], "required": false}, {"id": "interests", "label": "Interests", "type": "text", "placeholder": "e.g. your interests", "required": false}, {"id": "occasion", "label": "Occasion", "type": "text", "placeholder": "e.g. your occasion", "required": false}]}];
let currentTool=0;
function getSession(){try{return JSON.parse(localStorage.getItem('suite_sess')||'null')}catch{return null}}
function saveSession(s){localStorage.setItem('suite_sess',JSON.stringify(s))}
function clearSession(){localStorage.removeItem('suite_sess')}
function switchTab(tab){
  document.querySelectorAll('.auth-tab').forEach((t,i)=>t.classList.toggle('active',i===(tab==='login'?0:1)));
  document.getElementById('login-form').style.display=tab==='login'?'':'none';
  document.getElementById('signup-form').style.display=tab==='signup'?'':'none';
}
async function doLogin(){
  const email=document.getElementById('login-email').value.trim(),pwd=document.getElementById('login-password').value;
  const err=document.getElementById('login-err');err.textContent='';
  try{
    const r=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password:pwd})});
    const d=await r.json();if(!r.ok)throw new Error(d.detail||'Login failed');
    saveSession(d);onLoggedIn(d);
  }catch(e){err.textContent=e.message}
}
async function doSignup(){
  const name=document.getElementById('signup-name').value.trim(),email=document.getElementById('signup-email').value.trim(),pwd=document.getElementById('signup-password').value;
  const err=document.getElementById('signup-err');err.textContent='';
  try{
    const r=await fetch('/api/auth/signup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name,email,password:pwd})});
    const d=await r.json();if(!r.ok)throw new Error(d.detail||'Signup failed');
    saveSession(d);onLoggedIn(d);
  }catch(e){err.textContent=e.message}
}
function onLoggedIn(s){
  document.getElementById('auth-overlay').style.display='none';
  document.getElementById('user-chip').style.display='flex';
  document.getElementById('user-name').textContent=s.name||s.email||'';
  document.getElementById('user-avatar').textContent=(s.name||s.email||'?')[0].toUpperCase();
}
function logout(){clearSession();location.reload()}
function renderField(inp,ti){
  const id='t'+ti+'_'+inp.id;
  if(inp.type==='textarea')return '<div class="field"><label>'+inp.label+'</label><textarea id="'+id+'" placeholder="'+(inp.placeholder||'')+'"></textarea></div>';
  if(inp.type==='select'){const opts=(inp.options||[]).map(o=>'<option value="'+o+'">'+o+'</option>').join('');return'<div class="field"><label>'+inp.label+'</label><select id="'+id+'"><option value="">— Select —</option>'+opts+'</select></div>'}
  return'<div class="field"><label>'+inp.label+'</label><input type="'+(inp.type||'text')+'" id="'+id+'" placeholder="'+(inp.placeholder||'')+'" /></div>';
}
function buildUI(){
  const nav=document.getElementById('sidebar-nav'),content=document.getElementById('content');
  nav.innerHTML='';content.innerHTML='';
  TOOLS.forEach((tool,i)=>{
    const ni=document.createElement('div');ni.className='nav-item'+(i===0?' active':'');
    ni.innerHTML='<span class="nav-dot"></span>'+tool.name;ni.onclick=()=>switchTool(i);nav.appendChild(ni);
    const panel=document.createElement('div');panel.className='tool-panel'+(i===0?' active':'');panel.id='panel-'+i;
    panel.innerHTML='<div class="form-col">'+tool.inputs.map(inp=>renderField(inp,i)).join('')+'<button class="run-btn" id="run-'+i+'" onclick="runTool('+i+')"><span>Generate</span><span style="font-size:16px">→</span></button></div><div class="output-col"><div class="output-label">OUTPUT</div><div class="output-box" id="output-'+i+'"><div class="output-empty"><span class="icon">✦</span><span style="font-size:12px">Fill in the form and hit Generate</span></div></div><button class="copy-btn" id="copy-'+i+'" onclick="copyOutput('+i+')">Copy output</button></div>';
    content.appendChild(panel);
  });
  updateTopbar();
}
function switchTool(idx){
  document.querySelectorAll('.nav-item').forEach((el,i)=>el.classList.toggle('active',i===idx));
  document.querySelectorAll('.tool-panel').forEach((el,i)=>el.classList.toggle('active',i===idx));
  currentTool=idx;updateTopbar();
}
function updateTopbar(){const t=TOOLS[currentTool];document.getElementById('topbar-title').textContent=t.name;document.getElementById('topbar-tag').textContent=t.tagline}
async function runTool(idx){
  const tool=TOOLS[idx],btn=document.getElementById('run-'+idx),outBox=document.getElementById('output-'+idx),copyBtn=document.getElementById('copy-'+idx);
  let prompt=tool.promptTemplate;
  for(const inp of tool.inputs){const el=document.getElementById('t'+idx+'_'+inp.id);const val=el?el.value.trim():'';prompt=prompt.split('{{'+inp.id+'}}').join(val||'['+inp.label+']');}
  btn.disabled=true;btn.innerHTML='<span class="spinner"></span><span>Generating…</span>';
  outBox.innerHTML='<div class="output-empty"><span style="font-size:12px">Thinking…</span></div>';copyBtn.classList.remove('visible');
  try{
    const r=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_idx:idx,prompt})});
    if(!r.ok)throw new Error('Request failed: '+r.status);
    const data=await r.json();const text=data.result||'';
    outBox.innerHTML=formatOutput(text,tool.resultFormat);copyBtn.classList.add('visible');copyBtn.dataset.text=text;
  }catch(e){outBox.innerHTML='<div style="color:#f87171;font-size:13px">Error: '+e.message+'</div>'}
  finally{btn.disabled=false;btn.innerHTML='<span>Generate</span><span style="font-size:16px">→</span>'}
}
function formatOutput(text,format){
  if(format==='list'){const lines=text.split('\\n').filter(l=>l.trim());return'<ul>'+lines.map(l=>'<li>'+l.replace(/^[-•*\\d+\\.]+\\s*/,'')+'</li>').join('')+'</ul>'}
  if(format==='steps'){const lines=text.split('\\n').filter(l=>l.trim());return'<ol>'+lines.map(l=>'<li>'+l.replace(/^\\d+\\.?\\s*/,'')+'</li>').join('')+'</ol>'}
  return text.replace(/^### (.+)$/gm,'<h3>$1</h3>').replace(/^## (.+)$/gm,'<h2>$1</h2>').replace(/^# (.+)$/gm,'<h1>$1</h1>').replace(/\\*\\*(.+?)\\*\\*/g,'<strong>$1</strong>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/^- (.+)$/gm,'<li>$1</li>').replace(/\\n\\n/g,'<br><br>');
}
function copyOutput(idx){const btn=document.getElementById('copy-'+idx);navigator.clipboard.writeText(btn.dataset.text||'').then(()=>{btn.textContent='Copied!';setTimeout(()=>btn.textContent='Copy output',2000)})}
(function init(){if(AUTH_ENABLED){const s=getSession();if(s)onLoggedIn(s);else document.getElementById('auth-overlay').style.display='flex'}buildUI()})();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


# ── Auth ──────────────────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    email: str
    password: str
    name: str = ""

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

@app.post("/api/auth/signup")
def signup(req: AuthRequest):
    token = secrets.token_hex(32)
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (email, name, password, token) VALUES (?, ?, ?, ?)",
                (req.email.lower(), req.name or req.email.split("@")[0], hash_pw(req.password), token)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(400, detail="Email already registered")
    return {"email": req.email, "name": req.name or req.email.split("@")[0], "token": token}

@app.post("/api/auth/login")
def login(req: AuthRequest):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?",
            (req.email.lower(), hash_pw(req.password))
        ).fetchone()
    if not row:
        raise HTTPException(401, detail="Invalid email or password")
    return {"email": row["email"], "name": row["name"], "token": row["token"]}


# ── Generate ──────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    tool_idx: int
    prompt: str

@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if not GROQ_API_KEY:
        raise HTTPException(400, detail="NO_KEY -- add GROQ_API_KEY to .env")
    if req.tool_idx < 0 or req.tool_idx >= len(SYSTEM_PROMPTS):
        raise HTTPException(400, detail="Invalid tool_idx")
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPTS[req.tool_idx]},
                    {"role": "user",   "content": req.prompt},
                ],
                "max_tokens": 1500,
            },
        )
        r.raise_for_status()
        result = r.json()["choices"][0]["message"]["content"]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO queries (tool_idx, prompt, result) VALUES (?, ?, ?)",
            (req.tool_idx, req.prompt, result)
        )
        conn.commit()
    return {"result": result}


# ── History ───────────────────────────────────────────────────────────────────

@app.get("/api/history")
def history(tool_idx: int = 0):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, prompt, result, ts FROM queries WHERE tool_idx=? ORDER BY ts DESC LIMIT 20",
            (tool_idx,)
        ).fetchall()
    return [dict(r) for r in rows]


# ── Health / Setup ────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Health ", "ai_ready": bool(GROQ_API_KEY)}

class SetupRequest(BaseModel):
    api_key: str

@app.post("/api/setup")
def setup(req: SetupRequest):
    key = req.api_key.strip()
    if not key.startswith("gsk_"):
        raise HTTPException(400, detail="Invalid key -- Groq keys start with gsk_")
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, "w") as f:
        f.write("GROQ_API_KEY=" + key + "\n")
    os.environ["GROQ_API_KEY"] = key
    global GROQ_API_KEY
    GROQ_API_KEY = key
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
