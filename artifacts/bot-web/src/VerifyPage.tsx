import { useEffect, useRef, useState } from 'react';

type Stage = 'verifying' | 'success' | 'duplicate' | 'failed';

async function sha256(str: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, '0')).join('');
}

function canvasFingerprint(): string {
  try {
    const c = document.createElement('canvas');
    c.width = 200; c.height = 50;
    const ctx = c.getContext('2d')!;
    ctx.textBaseline = 'top';
    ctx.font = '14px Arial';
    ctx.fillStyle = '#f60';
    ctx.fillRect(125, 1, 62, 20);
    ctx.fillStyle = '#069';
    ctx.fillText('TGStarBot🔐', 2, 15);
    ctx.fillStyle = 'rgba(102,204,0,0.7)';
    ctx.fillText('TGStarBot🔐', 4, 17);
    return c.toDataURL();
  } catch { return 'no-canvas'; }
}

function webglInfo(): string {
  try {
    const c = document.createElement('canvas');
    const gl = (c.getContext('webgl') || c.getContext('experimental-webgl')) as WebGLRenderingContext | null;
    if (!gl) return 'no-webgl';
    const dbg = gl.getExtension('WEBGL_debug_renderer_info');
    return dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
  } catch { return 'no-webgl'; }
}

const STEPS = [
  [15,  'Reading browser info...'],
  [35,  'Collecting screen data...'],
  [55,  'Generating canvas fingerprint...'],
  [75,  'Processing device signature...'],
  [92,  'Submitting for verification...'],
] as [number, string][];

export default function VerifyPage({ token }: { token: string }) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState('Initializing...');
  const [stage, setStage] = useState<Stage>('verifying');
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;

    (async () => {
      // Animate progress steps
      for (const [pct, msg] of STEPS) {
        await new Promise((r) => setTimeout(r, 420));
        setProgress(pct);
        setStatusText(msg as string);
      }

      const canvas = canvasFingerprint();
      const webgl = webglInfo();
      const raw = [
        navigator.userAgent,
        `${screen.width}x${screen.height}x${screen.colorDepth}`,
        new Date().getTimezoneOffset(),
        navigator.language,
        navigator.hardwareConcurrency || 0,
        (navigator as any).deviceMemory || 0,
        navigator.platform || '',
        navigator.cookieEnabled,
        canvas,
        webgl,
      ].join('||');

      const fp = await sha256(raw);
      setProgress(97);
      setStatusText('Submitting...');

      try {
        const res = await fetch('/api/fingerprint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token, fingerprint: fp }),
        });
        const data = await res.json();
        setProgress(100);
        setStatusText('');

        if (data.ok) setStage('success');
        else if (data.reason === 'duplicate_device') setStage('duplicate');
        else setStage('failed');
      } catch {
        setStage('failed');
        setStatusText('Network error. Please try again.');
      }
    })();
  }, [token]);

  const s: Record<string, React.CSSProperties> = {
    root: { minHeight: '100vh', background: 'linear-gradient(135deg,#0f0f1a 0%,#1a1a2e 50%,#0d0d1f 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: "'Segoe UI',system-ui,sans-serif", color: '#e0e0ff', padding: 24 },
    card: { background: 'rgba(26,26,46,.92)', border: '1px solid rgba(124,107,255,.3)', borderRadius: 24, padding: '48px 36px', maxWidth: 360, width: '100%', textAlign: 'center', boxShadow: '0 20px 60px rgba(0,0,0,.6)' },
    icon: { fontSize: 56, marginBottom: 16 },
    h1: { fontSize: 22, fontWeight: 800, marginBottom: 10, color: '#fff' },
    p: { fontSize: 14, color: '#8888aa', lineHeight: 1.7, marginBottom: 24 },
    spinner: { width: 48, height: 48, border: '4px solid #2a2a4a', borderTopColor: '#7c6bff', borderRadius: '50%', margin: '0 auto 20px', animation: 'spin 1s linear infinite' },
    bar: { background: '#2a2a4a', borderRadius: 8, height: 6, marginBottom: 12, overflow: 'hidden' },
    fill: { height: '100%', background: 'linear-gradient(90deg,#7c6bff,#a78bfa)', borderRadius: 8, transition: 'width 0.4s ease', width: `${progress}%` },
    status: { fontSize: 13, color: '#6666aa' },
    btn: { marginTop: 20, background: 'linear-gradient(135deg,#7c6bff,#a855f7)', color: '#fff', border: 'none', borderRadius: 12, padding: '12px 28px', fontSize: 15, fontWeight: 700, cursor: 'pointer', textDecoration: 'none', display: 'inline-block' },
  };

  return (
    <div style={s.root}>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      <div style={s.card}>
        {stage === 'verifying' && (
          <>
            <div style={s.icon}>🔍</div>
            <h1 style={s.h1}>Verifying Device</h1>
            <p style={s.p}>Checking your device silently.<br />This takes just a second...</p>
            <div style={s.spinner} />
            <div style={s.bar}><div style={s.fill} /></div>
            <div style={s.status}>{statusText}</div>
          </>
        )}

        {stage === 'success' && (
          <>
            <div style={{ fontSize: 64, marginBottom: 16 }}>✅</div>
            <h1 style={{ ...s.h1, color: '#4ade80' }}>Device Verified!</h1>
            <p style={s.p}>Your device has been successfully verified.<br />Go back to the bot and tap <strong>✅ I'm Verified</strong>.</p>
            <a href="https://t.me/FREE_ST44R_BOT" style={s.btn}>Back to Bot</a>
          </>
        )}

        {stage === 'duplicate' && (
          <>
            <div style={{ fontSize: 64, marginBottom: 16 }}>🚫</div>
            <h1 style={{ ...s.h1, color: '#f87171' }}>Device Blocked</h1>
            <p style={s.p}>This device is already linked to another Telegram account.<br />One device can only be used with one account.</p>
          </>
        )}

        {stage === 'failed' && (
          <>
            <div style={{ fontSize: 64, marginBottom: 16 }}>❌</div>
            <h1 style={{ ...s.h1, color: '#f87171' }}>Verification Failed</h1>
            <p style={s.p}>Invalid or expired link.<br />Please send /start in the bot to get a new link.</p>
            <a href="https://t.me/FREE_ST44R_BOT" style={s.btn}>Back to Bot</a>
          </>
        )}
      </div>
    </div>
  );
}
