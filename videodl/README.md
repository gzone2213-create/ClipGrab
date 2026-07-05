# ClipGrab — Video Downloader (Flask API + Blogger Frontend)

FYP project: paste a YouTube / Facebook / Instagram / TikTok / Twitter(X) link,
see title, thumbnail, duration, and download in the available qualities
(video buttons 144p–4K when present, plus an MP3 audio option).

## 1. Project structure

```
videodl/
├── app.py                 # Flask app factory, CORS, rate limiting
├── routes.py              # /api/health, /api/info, /api/download
├── services.py            # yt-dlp extraction + format selection logic
├── utils.py                # URL validation, platform detection, formatting
├── requirements.txt
├── Procfile                # gunicorn start command for Render
├── runtime.txt              # Python version pin
├── .env.example
├── templates/
│   └── index.html          # local test page (same UI as Blogger)
├── static/
│   ├── css/style.css
│   └── js/app.js
└── blogger/
    └── theme.xml            # full Blogger theme with the app baked in
```

## 2. How it works

1. User pastes a URL into the search bar and clicks **Get video**.
2. Frontend calls `POST {API_BASE_URL}/api/info` with `{ "url": "..." }`.
3. Backend validates the URL, detects the platform, and runs `yt-dlp`
   (no download — just metadata) to collect title, thumbnail, duration,
   uploader, and every video/audio format available.
4. Backend groups formats into the standard ladder (144p/240p/360p/480p/
   720p/1080p/1440p/4K) and picks the best stream per rung, plus the
   best audio-only stream for the MP3 button.
5. Frontend renders the result card and one button per available quality.
6. Clicking a quality button calls `POST {API_BASE_URL}/api/download`
   with the chosen `format_id`, which resolves a direct, time-limited
   URL from yt-dlp. The frontend opens that link in a new tab so the
   browser handles the actual download.

## 3. Run locally

```bash
cd videodl
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` — this is the same UI/JS that ships inside
the Blogger theme, so you can demo and debug entirely offline before
touching Blogger at all.

Quick API test:
```bash
curl -X POST http://localhost:5000/api/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## 4. Deploy the backend (GitHub → Render)

**Step 1 — GitHub repo**
```bash
cd videodl
git init
git add .
git commit -m "ClipGrab backend"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

**Step 2 — Create the Render service**
1. Go to Render → New → Web Service.
2. Connect the GitHub repo you just pushed.
3. Runtime: Python 3 (Render reads `runtime.txt` automatically).
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app --workers 2 --timeout 120`
   (already in `Procfile`, Render picks it up automatically too).

**Step 3 — Environment variables**
On the Render service → Environment tab, add:
| Key | Value |
|---|---|
| `CORS_ORIGINS` | `https://your-blog-name.blogspot.com` (or `*` while testing) |

**Step 4 — Get your API URL**
After deploy finishes, Render gives you a URL like:
`https://clipgrab-api.onrender.com`

Test it: `https://clipgrab-api.onrender.com/api/health` should return
`{"status": "ok"}`.

> Free Render instances sleep after inactivity — the first request
> after idle can take 20–50 seconds. Mention this during your demo so
> it doesn't look like a bug.

## 5. Publish the Blogger frontend

**Step 5 — Paste your API URL into the theme**
Open `blogger/theme.xml`, find this line near the top of `<head>`:
```js
const API_BASE_URL = "https://YOUR-RENDER-APP.onrender.com";
```
Replace it with your real Render URL (no trailing slash).

**Step 6 — Upload and publish**
1. Blogger dashboard → Theme → Edit HTML (dropdown arrow next to "Customize").
2. Select all existing theme XML and replace it with the contents of
   `blogger/theme.xml`.
3. Click Save. Blogger will complain if there's a stray tag — the XML
   in this repo has already been validated as well-formed.
4. View your blog: you should see the ClipGrab hero + search bar.

Blogger widget notes:
- The whole app (HTML + CSS + JS) lives inside one `HTML` widget in the
  `main` section, so it doesn't depend on Blogger's post feed/loop at all.
- `b:skin` holds the CSS (Blogger's required place for theme styles).
- The `<script>` block sits in the footer widget so it runs after the
  DOM elements above it exist.

## 6. Testing checklist before showing your supervisor

- [ ] `/api/health` returns `{"status": "ok"}` on Render.
- [ ] Paste a real YouTube link → title/thumbnail/formats appear.
- [ ] Try an unsupported site (e.g. a random blog URL) → clean error message.
- [ ] Try an empty/garbage string → "not a valid URL" message, no crash.
- [ ] Click a quality button → new tab opens with the file/stream.
- [ ] Toggle dark/light mode → persists on reload (localStorage).
- [ ] Resize to mobile width → layout doesn't break.

## 7. Notes on legality / scope for your defense

`yt-dlp` reads publicly available streaming URLs the same way a browser
does when playing the video; it does not bypass DRM or authentication.
Downloading content still needs to respect each platform's Terms of
Service and the rights of the content owner — for a student FYP demo,
stick to your own uploads or clearly public/creative-commons content
when demonstrating live to your supervisor.

## 8. Likely viva questions and quick answers

- **"Why Flask and not Django?"** — Lightweight REST layer, no admin
  panel/ORM needed since there's no database; faster to justify for a
  single-purpose API.
- **"Why is the frontend on Blogger?"** — Free static hosting with a
  custom domain option; the actual app logic is 100% client-side JS
  talking to the Flask API, so Blogger only needs to serve HTML/CSS/JS.
- **"How do you handle different platforms?"** — `utils.detect_platform`
  matches the URL's domain against a whitelist before ever calling
  yt-dlp, so unsupported/malformed URLs fail fast with a clear message.
- **"How is quality selection done?"** — `services._select_video_formats`
  buckets yt-dlp's raw format list into the standard resolution ladder
  and picks the best (audio-inclusive, highest bitrate) format per rung.
