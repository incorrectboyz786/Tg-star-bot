import { useEffect, useState } from 'react';
import VerifyPage from './VerifyPage';

const BOT_USERNAME = 'FREE_ST44R_BOT';
const BOT_LINK = `https://t.me/${BOT_USERNAME}`;

function AnimatedStar({ style }: { style: React.CSSProperties }) {
  return (
    <span
      style={{
        position: 'absolute',
        fontSize: `${Math.random() * 12 + 8}px`,
        opacity: Math.random() * 0.5 + 0.2,
        animation: `float ${Math.random() * 4 + 3}s ease-in-out infinite`,
        animationDelay: `${Math.random() * 3}s`,
        ...style,
      }}
    >
      ⭐
    </span>
  );
}

function LandingPage() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCount((c) => (c >= 10000 ? 10000 : c + Math.floor(Math.random() * 37 + 3)));
    }, 80);
    return () => clearInterval(interval);
  }, []);

  const stars = Array.from({ length: 18 }, (_, i) => ({
    top: `${Math.random() * 90}%`,
    left: `${Math.random() * 90}%`,
  }));

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg,#0f0f1a 0%,#1a1a2e 50%,#0d0d1f 100%)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', fontFamily: "'Segoe UI',system-ui,sans-serif", color: '#e0e0ff', padding: '24px', overflow: 'hidden', position: 'relative' }}>

      <style>{`
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-16px)} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.6} }
        @keyframes glow { 0%,100%{box-shadow:0 0 20px rgba(124,107,255,.4)} 50%{box-shadow:0 0 40px rgba(124,107,255,.8),0 0 60px rgba(124,107,255,.3)} }
        @keyframes spin { to{transform:rotate(360deg)} }
        @keyframes countUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:none} }
        .feature-card:hover { transform:translateY(-4px) scale(1.02); box-shadow:0 20px 40px rgba(0,0,0,.4); }
        .cta-btn:hover { transform:translateY(-2px); box-shadow:0 12px 30px rgba(124,107,255,.6); }
        .cta-btn:active { transform:translateY(0); }
      `}</style>

      {stars.map((s, i) => <AnimatedStar key={i} style={s} />)}

      <div style={{ position: 'absolute', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle,rgba(124,107,255,.15) 0%,transparent 70%)', top: '50%', left: '50%', transform: 'translate(-50%,-50%)', pointerEvents: 'none' }} />

      <div style={{ background: 'rgba(26,26,46,.85)', backdropFilter: 'blur(20px)', border: '1px solid rgba(124,107,255,.3)', borderRadius: 24, padding: '48px 40px', maxWidth: 520, width: '100%', textAlign: 'center', position: 'relative', zIndex: 1, animation: 'glow 3s ease-in-out infinite' }}>

        <div style={{ fontSize: 72, marginBottom: 8, animation: 'float 3s ease-in-out infinite' }}>⭐</div>
        <h1 style={{ fontSize: 32, fontWeight: 800, margin: '0 0 8px', background: 'linear-gradient(90deg,#7c6bff,#a78bfa,#f0abfc)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          FREE STAR BOT
        </h1>
        <p style={{ color: '#8888cc', fontSize: 15, margin: '0 0 32px', lineHeight: 1.6 }}>
          Earn points by referring friends &amp; daily bonuses.<br />
          Redeem for real <strong style={{ color: '#a78bfa' }}>Telegram Stars ⭐</strong> — completely free!
        </p>

        <div style={{ background: 'rgba(124,107,255,.1)', border: '1px solid rgba(124,107,255,.2)', borderRadius: 16, padding: '20px 24px', marginBottom: 32 }}>
          <div style={{ fontSize: 13, color: '#6666aa', marginBottom: 4 }}>POINTS EARNED GLOBALLY</div>
          <div style={{ fontSize: 40, fontWeight: 800, color: '#a78bfa', fontVariantNumeric: 'tabular-nums', animation: 'countUp .3s ease' }}>
            {count.toLocaleString()}
          </div>
          <div style={{ fontSize: 12, color: '#4444aa', marginTop: 4 }}>⭐ Stars given away: {Math.floor(count / 100)}</div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 32 }}>
          {[
            { icon: '👥', title: 'Refer & Earn', desc: '+100 pts per referral' },
            { icon: '🎁', title: 'Daily Bonus', desc: 'Streak multipliers up to ×5' },
            { icon: '🔐', title: 'Secure', desc: 'Device fingerprint protection' },
            { icon: '⚡', title: 'Instant', desc: 'Auto approval & notification' },
          ].map((f) => (
            <div key={f.title} className="feature-card" style={{ background: 'rgba(255,255,255,.04)', border: '1px solid rgba(255,255,255,.08)', borderRadius: 14, padding: '16px 12px', transition: 'all .25s ease', cursor: 'default' }}>
              <div style={{ fontSize: 28, marginBottom: 6 }}>{f.icon}</div>
              <div style={{ fontWeight: 700, fontSize: 13, color: '#c4c4ff', marginBottom: 2 }}>{f.title}</div>
              <div style={{ fontSize: 11, color: '#6666aa' }}>{f.desc}</div>
            </div>
          ))}
        </div>

        <a href={BOT_LINK} target="_blank" rel="noreferrer" className="cta-btn" style={{ display: 'block', background: 'linear-gradient(135deg,#7c6bff,#a855f7)', color: '#fff', textDecoration: 'none', padding: '16px 32px', borderRadius: 14, fontWeight: 700, fontSize: 17, transition: 'all .25s ease', marginBottom: 16 }}>
          🚀 Start Earning Stars Free
        </a>
        <a href={BOT_LINK} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: '#6666aa', textDecoration: 'none' }}>
          @{BOT_USERNAME}
        </a>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 24 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ade80', animation: 'pulse 2s infinite' }} />
          <span style={{ fontSize: 12, color: '#4ade80' }}>Bot is online &amp; active</span>
        </div>
      </div>

      <p style={{ marginTop: 24, fontSize: 12, color: '#333355', position: 'relative', zIndex: 1 }}>
        Powered by Telegram Stars API · Secure · Free
      </p>
    </div>
  );
}

export default function App() {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const verifyToken = params.get('t');

  // Route /verify?t=TOKEN → device verification page
  if ((path === '/verify' || path.endsWith('/verify')) && verifyToken) {
    return <VerifyPage token={verifyToken} />;
  }

  return <LandingPage />;
}
