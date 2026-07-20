const { useState, useEffect } = React;

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [features] = useState([{"feature_name": "Live Telemetry Dashboard", "description": "Real-time event stream monitoring and status metrics.", "priority": "HIGH"}, {"feature_name": "Automated Opportunity Radar", "description": "AI agent recommendation feed highlighting high-value gaps.", "priority": "HIGH"}, {"feature_name": "One-Click Workspace Export", "description": "Export generated manifests and source code instantly.", "priority": "MEDIUM"}]);
  const [items] = useState([
    { id: 1, name: 'Live Stream Telemetry', status: 'ACTIVE', metrics: '99.9% Uptime' },
    { id: 2, name: 'Automated Gap Detection', status: 'OPTIMAL', metrics: '42 Opportunities' },
    { id: 3, name: 'Workflow Engine', status: 'RUNNING', metrics: '12 Jobs Active' }
  ]);

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto', fontFamily: "'Inter', sans-serif" }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h1 style={{ fontSize: '2.2rem', fontWeight: 800, background: 'linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              CreatorFlow AI
            </h1>
            <span className="tag">Creator Economy Dynamic Contract & Royalty Distribution</span>
          </div>
          <p style={{ color: '#94a3b8', marginTop: '0.5rem', fontSize: '1.05rem' }}>Next-Generation Autonomous Engine for Creator Economy Dynamic Contract & Royalty Distribution</p>
        </div>
        <button className="btn" onClick={() => alert('Live Prototype Action Executed!')}>
          Launch Demo Portal →
        </button>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
        <div className="card">
          <div style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Addressable Market (TAM)</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#60a5fa', marginTop: '0.5rem' }}>$4.5 Billion</div>
        </div>
        <div className="card">
          <div style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Opportunity Score</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#10b981', marginTop: '0.5rem' }}>8.7 / 10</div>
        </div>
        <div className="card">
          <div style={{ color: '#94a3b8', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Core Features</div>
          <div style={{ fontSize: '2rem', fontWeight: 700, color: '#c084fc', marginTop: '0.5rem' }}>3 Active</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.75rem' }}>
        {['dashboard', 'features', 'market-insights'].map(tab => (
          <button 
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              background: activeTab === tab ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              color: activeTab === tab ? '#60a5fa' : '#94a3b8',
              border: '1px solid ' + (activeTab === tab ? 'rgba(59, 130, 246, 0.4)' : 'transparent'),
              padding: '0.5rem 1.25rem',
              borderRadius: '8px',
              cursor: 'pointer',
              fontWeight: 600,
              textTransform: 'capitalize'
            }}
          >
            {tab.replace('-', ' ')}
          </button>
        ))}
      </div>

      {activeTab === 'dashboard' && (
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Live Operational Stream</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {items.map(item => (
              <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{item.name}</div>
                  <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>{item.metrics}</div>
                </div>
                <span className="tag" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>{item.status}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'features' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
          {features.map((feat, idx) => (
            <div key={idx} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <h4 style={{ fontWeight: 600 }}>{feat.feature_name}</h4>
                <span className="tag">{feat.priority}</span>
              </div>
              <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>{feat.description}</p>
            </div>
          ))}
        </div>
      )}

      {activeTab === 'market-insights' && (
        <div className="card">
          <h3 style={{ marginBottom: '1rem' }}>Market Differentiation Strategy</h3>
          <p style={{ color: '#cbd5e1', marginBottom: '1.5rem' }}><strong>Target Persona Insight:</strong> Mid-market team leads seeking instant visibility without complex 6-month deployment cycles.</p>
          <p style={{ color: '#cbd5e1' }}><strong>Differentiation Angle:</strong> Real-time WebSocket event streaming paired with single-click interactive prototype execution.</p>
        </div>
      )}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
