import os
import random
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response
import requests
import uvicorn

# =========================
# CONFIG
# =========================

PASSWORD = os.environ.get("SPACE_PASSWORD", "changeme")

OPENROUTER_KEYS = [
    v for k, v in os.environ.items()
    if k.startswith("OPENROUTER_KEY_")
]

if not OPENROUTER_KEYS:
    raise Exception("No OpenRouter API keys found!")

# =========================
# APP
# =========================

app = FastAPI()

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "super-secret-key")
)

# =========================
# HELPERS
# =========================

def get_random_key():
    return random.choice(OPENROUTER_KEYS)

def is_logged_in(request: Request):
    return request.session.get("authenticated") == True

# =========================
# LOGIN PAGE
# =========================

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Protected OpenWebUI</title>
    <style>
        body {
            font-family: Arial;
            background: #111;
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }

        .box {
            background: #222;
            padding: 30px;
            border-radius: 10px;
            width: 320px;
        }

        input {
            width: 100%;
            padding: 10px;
            margin-top: 10px;
            border-radius: 5px;
            border: none;
        }

        button {
            width: 100%;
            padding: 10px;
            margin-top: 15px;
            background: #444;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }

        button:hover {
            background: #666;
        }
    </style>
</head>
<body>
    <div class="box">
        <h2>OpenWebUI Login</h2>
        <form method="post" action="/login">
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>
"""

# =========================
# ROUTES
# =========================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    if not is_logged_in(request):
        return HTMLResponse(LOGIN_HTML)

    return HTMLResponse("""
    <html>
    <body style="background:#111;color:white;font-family:Arial;padding:30px">
        <h1>OpenWebUI Protected Space</h1>
        <p>Authentication successful.</p>

        <form method="post" action="/chat">
            <textarea name="prompt"
                style="width:100%;height:150px;background:#222;color:white"></textarea>

            <br><br>

            <button type="submit">Send</button>
        </form>
    </body>
    </html>
    """)

@app.post("/login")
async def login(request: Request, password: str = Form(...)):

    if password == PASSWORD:
        request.session["authenticated"] = True
        return RedirectResponse("/", status_code=302)

    return HTMLResponse(
        "<h2 style='color:red'>Wrong password</h2>",
        status_code=401
    )

@app.post("/chat")
async def chat(request: Request, prompt: str = Form(...)):

    if not is_logged_in(request):
        return RedirectResponse("/", status_code=302)

    key = get_random_key()

    headers = {
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://huggingface.co",
        "X-Title": "HF OpenWebUI"
    }

    payload = {
    # Default free OpenRouter routing
    "model": "openrouter/auto",

    # Prefer free models only
    "route": "fallback",

    # Extra provider preferences
    "provider": {
        "allow_fallbacks": True,
        "data_collection": "deny"
    },

    # Message content
    "messages": [
        {
            "role": "user",
            "content": prompt
        }
    ]
}

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=120
    )

    result = response.json()

    try:
        output = result["choices"][0]["message"]["content"]
    except:
        output = str(result)

    return HTMLResponse(f"""
    <html>
    <body style="background:#111;color:white;font-family:Arial;padding:30px">
        <h2>Response</h2>

        <div style="
            background:#222;
            padding:20px;
            border-radius:10px;
            white-space:pre-wrap;
        ">
        {output}
        </div>

        <br>

        <a href="/" style="color:cyan">Back</a>
    </body>
    </html>
    """)

# =========================
# START
# =========================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=7860
    )
