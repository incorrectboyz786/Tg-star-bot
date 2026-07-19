"""HTML page served for device fingerprint verification."""


def get_verify_html(token: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Device Verification</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    min-height: 100vh;
    background: #0f0f1a;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Segoe UI', system-ui, sans-serif;
    color: #e0e0ff;
  }}
  .card {{
    background: #1a1a2e;
    border: 1px solid #2a2a4a;
    border-radius: 20px;
    padding: 40px 32px;
    max-width: 360px; width: 90%;
    text-align: center;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }}
  .icon {{ font-size: 52px; margin-bottom: 16px; }}
  h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 8px; color: #fff; }}
  p {{ font-size: 14px; color: #8888aa; margin-bottom: 24px; line-height: 1.6; }}
  .spinner {{
    width: 48px; height: 48px;
    border: 4px solid #2a2a4a;
    border-top-color: #7c6bff;
    border-radius: 50%;
    margin: 0 auto 20px;
    animation: spin 1s linear infinite;
  }}
  @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  .progress {{
    background: #2a2a4a; border-radius: 8px; height: 6px;
    margin-bottom: 16px; overflow: hidden;
  }}
  .progress-bar {{
    height: 100%; width: 0%;
    background: linear-gradient(90deg, #7c6bff, #a78bfa);
    border-radius: 8px;
    transition: width 0.4s ease;
  }}
  .status {{ font-size: 13px; color: #6666aa; margin-bottom: 4px; }}
  .success {{ color: #4ade80; }}
  .blocked {{ color: #f87171; }}
  .check {{ font-size: 64px; }}
  .btn {{
    margin-top: 20px;
    background: #7c6bff;
    color: #fff;
    border: none;
    border-radius: 12px;
    padding: 12px 28px;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
  }}
</style>
</head>
<body>
<div class="card" id="card">
  <div class="icon">🔍</div>
  <h1>Device Verification</h1>
  <p>Collecting device information securely. This takes just a second...</p>
  <div class="spinner" id="spinner"></div>
  <div class="progress"><div class="progress-bar" id="bar"></div></div>
  <div class="status" id="status">Initializing...</div>
</div>

<script>
const TOKEN = {repr(token)};
const STEPS = [
  [10, "Reading browser info..."],
  [30, "Collecting screen data..."],
  [55, "Generating canvas fingerprint..."],
  [75, "Processing device signature..."],
  [90, "Submitting for verification..."],
];

const bar = document.getElementById('bar');
const status = document.getElementById('status');

function setProgress(pct, msg) {{
  bar.style.width = pct + '%';
  status.textContent = msg;
}}

async function sha256(str) {{
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,'0')).join('');
}}

function canvasFingerprint() {{
  try {{
    const c = document.createElement('canvas');
    c.width = 200; c.height = 50;
    const ctx = c.getContext('2d');
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('TGStarBot🔐', 2, 15);
    ctx.fillStyle = 'rgba(102,204,0,0.7)';
    ctx.fillText('TGStarBot🔐', 4, 17);
    return c.toDataURL();
  }} catch(e) {{ return 'no-canvas'; }}
}}

function webglInfo() {{
  try {{
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
    if (!gl) return 'no-webgl';
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    return dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  }} catch(e) {{ return 'no-webgl'; }}
}}

function audioFingerprint() {{
  try {{
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const analyser = ctx.createAnalyser();
    const gain = ctx.createGain();
    gain.gain.value = 0;
    osc.connect(analyser); analyser.connect(gain); gain.connect(ctx.destination);
    osc.start(0); osc.stop(0.001);
    const data = new Float32Array(analyser.frequencyBinCount);
    analyser.getFloatFrequencyData(data);
    ctx.close();
    return data.slice(0, 10).join(',');
  }} catch(e) {{ return 'no-audio'; }}
}}

async function collectAndSubmit() {{
  let step = 0;
  const tick = setInterval(() => {{
    if (step < STEPS.length) {{
      setProgress(STEPS[step][0], STEPS[step][1]);
      step++;
    }}
  }}, 400);

  await new Promise(r => setTimeout(r, 400 * STEPS.length + 200));
  clearInterval(tick);

  const canvas = canvasFingerprint();
  const webgl = webglInfo();
  const audio = audioFingerprint();

  const raw = [
    navigator.userAgent,
    screen.width + 'x' + screen.height + 'x' + screen.colorDepth,
    new Date().getTimezoneOffset(),
    navigator.language,
    navigator.hardwareConcurrency || 0,
    navigator.deviceMemory || 0,
    navigator.platform || '',
    navigator.cookieEnabled,
    canvas,
    webgl,
    audio,
  ].join('||');

  setProgress(92, 'Hashing signature...');
  const fp = await sha256(raw);
  setProgress(97, 'Submitting...');

  try {{
    const res = await fetch('/api/fingerprint', {{
      method: 'POST',
      headers: {{ 'Content-Type': 'application/json' }},
      body: JSON.stringify({{ token: TOKEN, fingerprint: fp }}),
    }});
    const data = await res.json();
    setProgress(100, '');

    const card = document.getElementById('card');
    if (data.ok) {{
      card.innerHTML = `
        <div class="check">✅</div>
        <h1 class="success">Device Verified!</h1>
        <p>Your device has been successfully verified.<br>Go back to the bot and tap <b>✅ I'm Verified</b>.</p>
        <a href="https://t.me/" class="btn">Back to Bot</a>
      `;
    }} else if (data.reason === 'duplicate_device') {{
      card.innerHTML = `
        <div class="check">🚫</div>
        <h1 class="blocked">Device Blocked</h1>
        <p>This device is already linked to another Telegram account.<br>One device can only be used with one account.</p>
      `;
    }} else {{
      card.innerHTML = `
        <div class="check">❌</div>
        <h1 class="blocked">Verification Failed</h1>
        <p>Invalid or expired verification link.<br>Please send /start in the bot to get a new link.</p>
      `;
    }}
  }} catch(e) {{
    setProgress(0, 'Network error. Please try again.');
  }}
}}

collectAndSubmit();
</script>
</body>
</html>"""
