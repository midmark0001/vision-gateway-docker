import os, json, time, uuid, base64
from curl_cffi import requests

# ── Runtime string decoder ──────────────────────────────────
_K = "nqv9x2k7p4"
def _x(e):
    b = base64.b64decode(e)
    return ''.join(chr(v ^ ord(_K[i % len(_K)])) for i, v in enumerate(b))

# ── Decoded constants ───────────────────────────────────────
_SF   = _x("DwEGZhlHH18vRxoQAlxWWBhYHg==")
_REQ  = _x("BgUCSQsIRBgBQQcdGlsXRkVUH1lBEAZQV1YEVAVEBx8TFhxdCEIdUQAFBQ==")
_DOM  = _x("HwQfVRRQBENeVwEc")
_LOGIN= _x("BgUCSQsIRBgBQQcdGlsXRkVUH1lBEAZQV1MeQxgbBwIFTB0fH1gbUQA=")
_PRF  = _x("BgUCSQsIRBgBQQcdGlsXRkVUH1lBEAZQV1MeQxgbCRQCFBlRCFgFWhpcElwMUwJbAw==")
_UA   = _x("Ix4MUBReChhFGl5RXm4RXA9YB0dOPyIZSQJFB0sUORgYD0wJS09GAEdRN0kIXg5gFVYlGAIWTQFcGUMCTlk9cSx/JxtQWAcaExk/VwhcHx1OMh5LF18OGEEAV19GF0gcWxcjVQgQBFBXB1gAXgdY")
_ACC  = _x("DwEGVRFRCkMZWwBeHEoXXEcXBFEWBVlJFFMCWVwURF5c")
_CID  = _x("DxhbWhBTHw==")
_LG   = _x("Ij4xcDY=")
_KEY  = _x("LzgMWCtLKl8oAwYWIUo/WDIaPFtYFAdOMl8eZSUGFgk4ayxrXFwh")

_BASE = f"https://{_DOM}"

def _load_state():
    if os.path.exists(_SF):
        with open(_SF) as f:
            return json.load(f)
    return {}

def _save_state(cookies, token, firebase, email):
    with open(_SF, "w") as f:
        json.dump({
            _x("CBgEXBpTGFIvQAEaE1c="): firebase,
            _x("DQQFTRdfNEMfXwsf"): token,
            "email": email,
            "ts": time.time()
        }, f)

def _fetch_token():
    s = _load_state()
    return s.get(_x("CBgEXBpTGFIvQAEaE1c="))

# ── Upload handler ──────────────────────────────────────────
def _upload_file(path, tok, session):
    if not os.path.exists(path):
        return None
    fn = os.path.basename(path)
    meta = {
        "name": fn,
        "documentMeta": {"file_name": fn},
        "namespace": _CID,
        "dirPath": ""
    }
    hdrs = {
        "User-Agent": _UA,
        "Accept": _ACC,
        "Origin": _BASE,
        "Referer": f"{_DOM}/ai-chat",
        "platform-type": "webapp",
        "qb-product": "AI-CHAT",
        "useridtoken": tok
    }
    r1 = session.post(_REQ, json=meta, headers=hdrs, impersonate="chrome")
    if r1.status_code not in [200, 201]:
        return r1
    did = r1.json()["data"]["id"]
    cu = f"{_BASE}/api/docupine/documents/{did}/content"
    beaver = {"x-beaver-asset": "storage", "x-beaver-source": "ai-chat", "x-beaver-tenant": _DOM}
    hdrs.update(beaver)
    session.headers.update(beaver)
    from requests_toolbelt import MultipartEncoder
    with open(path, "rb") as f:
        content = f.read()
    me = MultipartEncoder({"file": (fn, content, "application/octet-stream")})
    hdrs["Content-Type"] = me.content_type
    return session.put(cu, data=me, headers=hdrs, impersonate="chrome")

# ── Chrome bootstrap ────────────────────────────────────────
def _get_cookies():
    import undetected_chromedriver as uc
    from webdriver_manager.chrome import ChromeDriverManager
    opt = uc.ChromeOptions()
    opt.add_argument("--headless")
    drv = uc.Chrome(options=opt, driver_executable_path=ChromeDriverManager().install())
    try:
        drv.get(_BASE)
        time.sleep(8)
        return drv.get_cookies()
    finally:
        drv.quit()

# ── Auth flow ───────────────────────────────────────────────
def _auth(usr, pwd):
    s = requests.Session()
    try:
        for c in _get_cookies():
            s.cookies.set(c['name'], c['value'], domain=_DOM)
    except:
        pass

    hdrs = {"User-Agent": _UA, "Content-Type": "application/json", "Origin": _BASE, "Referer": f"{_DOM}/"}
    id_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={_KEY}"
    r1 = s.post(id_url, json={"email": usr, "password": pwd, "returnSecureToken": True}, headers=hdrs, impersonate="chrome")
    if r1.status_code != 200:
        raise Exception(f"Auth failed: {r1.status_code}")
    id_t = r1.json()["idToken"]

    tp = {"token": id_t, "scope": "DESKTOP_WINDOWS"}
    r2 = s.post(_LOGIN, json=tp, headers=hdrs, impersonate="chrome")
    if r2.status_code != 200:
        raise Exception(f"Session error: {r2.status_code} {r2.text[:200]}")
    master = r2.json()["data"]["token"]
    _save_state(s.cookies.get_dict(), master, id_t, usr)
    return master

# ── Task runner ─────────────────────────────────────────────
def _run(usr, pwd, msg, fpath=None):
    s = requests.Session()
    st = _load_state()
    if not st:
        _auth(usr, pwd)
        st = _load_state()
    at = st.get(_x("DQQFTRdfNEMfXwsf"))
    ft = st.get(_x("CBgEXBpTGFIvQAEaE1c="))

    # Set BOTH cookies that the session needs
    s.cookies.set("useridtoken", at, domain=f".{_DOM}")

    mp = {"content": msg}

    if fpath and os.path.exists(fpath):
        ur = _upload_file(fpath, ft, s)
        if ur and ur.status_code in [401, 403]:
            s.cookies.clear()
            if os.path.exists(_SF):
                os.remove(_SF)
            _auth(usr, pwd)
            st = _load_state()
            at = st.get(_x("DQQFTRdfNEMfXwsf"))
            ft = st.get(_x("CBgEXBpTGFIvQAEaE1c="))
            s.cookies.set("useridtoken", at, domain=f".{_DOM}")
            ur = _upload_file(fpath, ft, s)
        if ur and ur.status_code in [200, 204]:
            ud = ur.json().get("data", {})
            ext = os.path.splitext(fpath)[1].lower() if fpath else ".png"
            mm = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
            mp["files"] = [{
                "id": ud.get("id"),
                "mimeType": mm.get(ext, "image/png"),
                "name": ud.get("name")
            }]

    cid = str(uuid.uuid4())
    url = f"{_BASE}/api/ai-chat/chat/conversation/{cid}"

    tp = {
        "message": mp,
        "context": {"editorContext": "", "selectionContext": "", "userDialect": "en-us", "apiVersion": 2},
        "origin": {"name": "ai-chat.chat", "url": "https://quillbot.com"}
    }

    hdrs = {
        "User-Agent": _UA,
        "accept": _ACC,
        "Origin": _BASE,
    }

    r = s.post(url, json=tp, headers=hdrs, impersonate="chrome", stream=True)
    if r.status_code in [401, 403]:
        s.cookies.clear()
        if os.path.exists(_SF):
            os.remove(_SF)
        _auth(usr, pwd)
        st = _load_state()
        at = st.get(_x("DQQFTRdfNEMfXwsf"))
        s.cookies.set("useridtoken", at, domain=f".{_DOM}")
        r = s.post(url, json=tp, headers=hdrs, impersonate="chrome", stream=True)

    parts = [l.decode() for l in r.iter_lines() if l]
    full_text = ""
    for part in parts:
        try:
            chunk = json.loads(part)
            if chunk.get("type") == "content":
                full_text += chunk.get("content", "")
        except:
            continue
    return full_text


from typing import Union
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Data Processing Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def hc():
    return {"status": "ok"}

@app.post("/api/v1/run-task")
async def ep(
    email: str = Form(...),
    password: str = Form(...),
    message: str = Form(...),
    image: Union[UploadFile, str, None] = File(None)
):
    tmp = None
    try:
        if image and isinstance(image, UploadFile) and image.filename:
            dn = "temp_gateway_uploads"
            os.makedirs(dn, exist_ok=True)
            tmp = os.path.join(dn, f"{uuid.uuid4().hex}_{image.filename}")
            with open(tmp, "wb") as bf:
                import shutil
                shutil.copyfileobj(image.file, bf)

        reply = _run(usr=email, pwd=password, msg=message, fpath=tmp)
        return {"status": "success", "result": reply}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if tmp and os.path.exists(tmp):
            try: os.remove(tmp)
            except: pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
