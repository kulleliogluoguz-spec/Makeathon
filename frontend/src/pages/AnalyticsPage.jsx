import { useState, useEffect } from 'react';

const CHANNEL_COLORS = {
  instagram: '#e1306c',
  messenger: '#0084ff',
  livechat: '#10b981',
  unknown: '#94a3b8',
};

const CHANNEL_LABELS = {
  instagram: 'Instagram',
  messenger: 'Messenger',
  livechat: 'Live Chat',
};

const STAGE_COLORS = {
  awareness: '#94a3b8',
  interest: '#3b82f6',
  consideration: '#8b5cf6',
  decision: '#f59e0b',
  purchase: '#10b981',
  objection: '#ef4444',
  post_purchase: '#06b6d4',
};

function MetricCard({ label, value, sub }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem',
      padding: '1.25rem', flex: 1, minWidth: '150px',
    }}>
      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '4px', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: '1.75rem', fontWeight: 600 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '2px' }}>{sub}</div>}
    </div>
  );
}

function BarChart({ data, colorFn, labelKey, valueKey, maxHeight }) {
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: maxHeight || '160px' }}>
      {data.map((d, i) => {
        const pct = ((d[valueKey] || 0) / max) * 100;
        const color = typeof colorFn === 'function' ? colorFn(d) : colorFn || '#3b82f6';
        return (
          <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%', justifyContent: 'flex-end' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 600, marginBottom: '4px' }}>{d[valueKey]}</div>
            <div style={{
              width: '100%', maxWidth: '60px', background: color,
              borderRadius: '4px 4px 0 0', height: `${Math.max(pct, 3)}%`,
              transition: 'height 0.3s',
            }} />
            <div style={{ fontSize: '0.65rem', color: '#6b7280', marginTop: '6px', textAlign: 'center' }}>
              {d[labelKey]}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MiniLineChart({ data }) {
  if (!data || data.length === 0) return null;
  const max = Math.max(...data.map(d => d.count), 1);
  const w = 100;
  const h = 40;
  const points = data.map((d, i) => {
    const x = (i / Math.max(data.length - 1, 1)) * w;
    const y = h - (d.count / max) * h;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: '120px' }} preserveAspectRatio="none">
      <polyline
        fill="none"
        stroke="#3b82f6"
        strokeWidth="1.5"
        points={points}
      />
      <polyline
        fill="url(#grad)"
        stroke="none"
        points={`0,${h} ${points} ${w},${h}`}
      />
      <defs>
        <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState('month');
  const [overview, setOverview] = useState(null);
  const [channels, setChannels] = useState([]);
  const [intentDist, setIntentDist] = useState([]);
  const [funnel, setFunnel] = useState([]);
  const [categories, setCategories] = useState([]);
  const [daily, setDaily] = useState([]);
  const [topProducts, setTopProducts] = useState([]);

  const load = async () => {
    const p = `period=${period}`;
    try {
      const [ov, ch, id, fn, ct, dl, tp] = await Promise.all([
        fetch(`/api/v1/analytics/overview?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/channels?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/intent-distribution?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/funnel?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/categories?${p}`).then(r => r.json()),
        fetch(`/api/v1/analytics/daily-volume?days=30`).then(r => r.json()),
        fetch(`/api/v1/analytics/top-products?${p}`).then(r => r.json()),
      ]);
      setOverview(ov);
      setChannels(ch.channels || []);
      setIntentDist(id.distribution || []);
      setFunnel(fn.funnel || []);
      setCategories(ct.categories || []);
      setDaily(dl.daily || []);
      setTopProducts(tp.products || []);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { load(); }, [period]);

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Analytics</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Performance overview across all channels</p>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          {[
            { value: 'today', label: 'Today' },
            { value: 'week', label: 'Week' },
            { value: 'month', label: 'Month' },
            { value: 'all', label: 'All Time' },
          ].map(opt => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              style={{
                padding: '6px 14px', fontSize: '0.8rem', borderRadius: '9999px',
                background: period === opt.value ? '#000' : '#fff',
                color: period === opt.value ? '#fff' : '#374151',
                border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500,
              }}
            >{opt.label}</button>
          ))}
        </div>
      </div>

      {/* Overview Cards */}
      {overview && (
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <MetricCard label="Conversations" value={overview.total_conversations} />
          <MetricCard label="Customers" value={overview.total_customers} />
          <MetricCard label="Messages" value={overview.total_messages} />
          <MetricCard label="Avg Intent Score" value={overview.avg_intent_score} />
          <MetricCard label="High Intent (70+)" value={overview.high_intent_count} sub="Ready to buy" />
          <MetricCard label="Active Today" value={overview.active_today} />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Channel Distribution */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Channel Distribution</h3>
          {channels.length === 0 ? (
            <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No data</div>
          ) : (
            <div>
              {channels.map((ch, i) => {
                const total = channels.reduce((s, c) => s + c.count, 0);
                const pct = total > 0 ? Math.round((ch.count / total) * 100) : 0;
                const color = CHANNEL_COLORS[ch.name] || '#94a3b8';
                return (
                  <div key={i} style={{ marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 500 }}>{CHANNEL_LABELS[ch.name] || ch.name}</span>
                      <span style={{ color: '#6b7280' }}>{ch.count} ({pct}%)</span>
                    </div>
                    <div style={{ height: '8px', background: '#f3f4f6', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: '4px' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Intent Score Distribution */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Intent Score Distribution</h3>
          <BarChart
            data={intentDist}
            labelKey="range"
            valueKey="count"
            colorFn={(d) => {
              if (d.range === '81-100') return '#10b981';
              if (d.range === '61-80') return '#3b82f6';
              if (d.range === '41-60') return '#f59e0b';
              return '#94a3b8';
            }}
          />
        </div>

        {/* Sales Funnel */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Sales Funnel</h3>
          <BarChart
            data={funnel}
            labelKey="stage"
            valueKey="count"
            colorFn={(d) => STAGE_COLORS[d.stage] || '#94a3b8'}
          />
        </div>

        {/* Category Breakdown */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Categories</h3>
          {categories.length === 0 ? (
            <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No data</div>
          ) : (
            categories.map((cat, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f3f4f6', fontSize: '0.85rem' }}>
                <span>{cat.name.replace(/_/g, ' ')}</span>
                <span style={{ fontWeight: 600 }}>{cat.count}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Daily Volume */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem', marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>Daily Conversation Volume (Last 30 Days)</h3>
        <MiniLineChart data={daily} />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#9ca3af', marginTop: '4px' }}>
          <span>{daily.length > 0 ? daily[0].date : ''}</span>
          <span>{daily.length > 0 ? daily[daily.length - 1].date : ''}</span>
        </div>
      </div>

      {/* Top Products */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.25rem' }}>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '1rem' }}>Top Mentioned Products</h3>
        {topProducts.length === 0 ? (
          <div style={{ color: '#9ca3af', fontSize: '0.875rem' }}>No product mentions yet</div>
        ) : (
          topProducts.map((p, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
              <div>
                <span style={{ fontWeight: 500, fontSize: '0.875rem' }}>{i + 1}. {p.name}</span>
              </div>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#3b82f6' }}>{p.mentions} mentions</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
