import { useState, useEffect } from 'react';
import { t } from '../lib/i18n';

const STATUS_OPTIONS = [
  { value: 'new', label: 'New', color: '#3b82f6' },
  { value: 'contacted', label: 'Contacted', color: '#f59e0b' },
  { value: 'responded', label: 'Responded', color: '#8b5cf6' },
  { value: 'converted', label: 'Converted', color: '#10b981' },
  { value: 'rejected', label: 'Rejected', color: '#94a3b8' },
];

export default function LeadFinderPage() {
  const [tab, setTab] = useState('find'); // 'find' or 'saved'
  const [personas, setPersonas] = useState([]);
  const [selectedPersona, setSelectedPersona] = useState('');
  const [icp, setIcp] = useState(null);
  const [leads, setLeads] = useState([]);
  const [savedLeads, setSavedLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [page, setPage] = useState(1);
  const [selectedLead, setSelectedLead] = useState(null);
  const [outreachMsg, setOutreachMsg] = useState('');
  const [generatingMsg, setGeneratingMsg] = useState(false);
  const [activePreset, setActivePreset] = useState('');
  const [linkedinKeywords, setLinkedinKeywords] = useState('');
  const [linkedinResults, setLinkedinResults] = useState([]);
  const [linkedinSearching, setLinkedinSearching] = useState(false);
  const [autoCalling, setAutoCalling] = useState(false);
  const [callResults, setCallResults] = useState([]);
  const [autoLandingPage, setAutoLandingPage] = useState(null);
  const [generatingLP, setGeneratingLP] = useState(false);

  useEffect(() => {
    fetch('/api/v1/personas/').then(r => r.json()).then(setPersonas).catch(() => {});
    loadSaved();
  }, []);

  const loadSaved = async () => {
    try {
      const resp = await fetch('/api/v1/leads/saved');
      if (resp.ok) setSavedLeads(await resp.json());
    } catch (e) {}
  };

  const generateICP = async () => {
    if (!selectedPersona) return;
    setActivePreset('');
    setLoading(true);
    try {
      const resp = await fetch('/api/v1/leads/generate-icp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona_id: selectedPersona }),
      });
      const data = await resp.json();
      setIcp(data.icp);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const searchLeads = async (p = 1) => {
    if (!icp) return;
    setSearching(true);
    setPage(p);
    setAutoLandingPage(null);
    try {
      const resp = await fetch('/api/v1/leads/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ icp, persona_id: selectedPersona, page: p }),
      });
      const data = await resp.json();
      const foundLeads = data.leads || [];
      setLeads(foundLeads);
      setTotalResults(data.total || 0);

      // Auto-generate landing page for the #1 lead
      if (foundLeads.length > 0 && p === 1) {
        const topLead = foundLeads[0];
        if (topLead.company_name) {
          autoGenerateLandingPage(topLead);
        }
      }
    } catch (e) { console.error(e); }
    setSearching(false);
  };

  const saveLead = async (lead) => {
    try {
      await fetch('/api/v1/leads/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...lead, persona_id: selectedPersona }),
      });
      loadSaved();
    } catch (e) { console.error(e); }
  };

  const updateLeadStatus = async (leadId, status) => {
    await fetch(`/api/v1/leads/saved/${leadId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    loadSaved();
  };

  const generateOutreach = async (lead, channel = 'email') => {
    setGeneratingMsg(true);
    try {
      const resp = await fetch('/api/v1/leads/outreach-message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead, icp, persona_id: selectedPersona, channel }),
      });
      const data = await resp.json();
      setOutreachMsg(data.message || '');
    } catch (e) {}
    setGeneratingMsg(false);
  };

  const deleteLead = async (id) => {
    if (!confirm('Remove this lead?')) return;
    await fetch(`/api/v1/leads/saved/${id}`, { method: 'DELETE' });
    loadSaved();
  };

  const searchLinkedIn = async () => {
    setLinkedinSearching(true);
    try {
      const resp = await fetch('/api/v1/linkedin/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keywords: linkedinKeywords, limit: 25 }),
      });
      const data = await resp.json();
      const people = data.people || [];
      setLinkedinResults(people);

      // Auto-generate landing page for the #1 result
      if (people.length > 0) {
        const topPerson = people[0];
        if (topPerson.company_name) {
          autoGenerateLandingPage(topPerson);
        }
      }
    } catch (e) { console.error(e); }
    setLinkedinSearching(false);
  };

  const sendInvite = async (person) => {
    const note = prompt('Connection request note (max 300 chars, leave empty for no note):',
      `Hi ${person.first_name}, I came across your profile and would love to connect!`);
    if (note === null) return;

    try {
      const resp = await fetch('/api/v1/linkedin/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: person.provider_id, message: note }),
      });
      const data = await resp.json();
      if (data.success) {
        alert(`Connection request sent to ${person.first_name}!`);
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (e) { alert('Failed to send invite'); }
  };

  const autoGenerateLandingPage = async (lead) => {
    setGeneratingLP(true);
    try {
      const resp = await fetch('/api/v1/landing-pages/auto-generate-for-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead, persona_id: selectedPersona }),
      });
      const data = await resp.json();
      if (data.success) {
        setAutoLandingPage(data);
      }
    } catch (e) { console.error(e); }
    setGeneratingLP(false);
  };

  const autoCallLeads = async (leadsToCall) => {
    if (!leadsToCall.length) {
      alert('No leads with score 70+ to call');
      return;
    }

    const leadsWithInfo = leadsToCall.filter(l => l.first_name && l.company_name);

    if (!confirm(`This will trigger AI phone calls to ${leadsWithInfo.length} leads. The AI will:\n\n1. Introduce your company\n2. Explain why we're reaching out\n3. Try to schedule a meeting with the sales manager\n\nProceed?`)) return;

    setAutoCalling(true);
    const results = [];

    for (const lead of leadsWithInfo) {
      try {
        const resp = await fetch('/api/v1/leads/auto-call', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lead, persona_id: selectedPersona }),
        });
        const data = await resp.json();

        if (!data.success && data.suggestion === 'send_linkedin_message') {
          if (lead.provider_id) {
            try {
              const msgResp = await fetch('/api/v1/leads/outreach-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ lead, icp: icp || {}, persona_id: selectedPersona, channel: 'linkedin' }),
              });
              const msgData = await msgResp.json();

              if (msgData.message) {
                const sendResp = await fetch('/api/v1/linkedin/invite', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ provider_id: lead.provider_id, message: msgData.message.slice(0, 300) }),
                });
                const sendData = await sendResp.json();

                results.push({
                  name: `${lead.first_name} ${lead.last_name}`,
                  company: lead.company_name,
                  status: sendData.success ? 'linkedin_sent' : 'failed',
                  error: sendData.error || '',
                });

                try {
                  await fetch('/api/v1/leads/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ...lead, persona_id: selectedPersona, status: 'contacted' }),
                  });
                } catch (e) {}

                await new Promise(r => setTimeout(r, 2000));
                continue;
              }
            } catch (e) {}
          }

          results.push({
            name: `${lead.first_name} ${lead.last_name}`,
            company: lead.company_name,
            status: 'no_phone',
            error: 'No phone number — LinkedIn invite sent instead',
          });
        } else {
          results.push({
            name: `${lead.first_name} ${lead.last_name}`,
            company: lead.company_name,
            status: data.success ? 'called' : 'failed',
            error: data.error || '',
            call_id: data.call_id || '',
          });

          try {
            await fetch('/api/v1/leads/save', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ ...lead, persona_id: selectedPersona, status: 'contacted' }),
            });
          } catch (e) {}
        }
      } catch (e) {
        results.push({
          name: `${lead.first_name} ${lead.last_name}`,
          status: 'error',
          error: e.message,
        });
      }

      await new Promise(r => setTimeout(r, 2000));
    }

    setCallResults(results);
    setAutoCalling(false);
    loadSaved();

    const succeeded = results.filter(r => r.status === 'called').length;
    const linkedin = results.filter(r => r.status === 'linkedin_sent' || r.status === 'no_phone').length;
    alert(`Done! ${succeeded} calls initiated, ${linkedin} LinkedIn invites sent, out of ${results.length} leads.`);
  };

  const autoCallLinkedinLeads = async (people) => {
    const saved = [];
    for (const person of people) {
      try {
        await fetch('/api/v1/leads/save', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...person,
            ai_score: 0,
            ai_reason: 'LinkedIn search result',
            ai_approach: '',
            persona_id: selectedPersona,
            status: 'new',
          }),
        });
        saved.push(person);
      } catch (e) {}
    }

    if (saved.length > 0) {
      autoCallLeads(saved);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.25rem' }}>Lead Finder</h1>
          <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>AI-powered lead generation — find your ideal customers</p>
        </div>
        <div style={{ display: 'flex', gap: '4px' }}>
          <button onClick={() => setTab('find')} style={{ padding: '6px 16px', fontSize: '0.85rem', borderRadius: '9999px', background: tab === 'find' ? '#000' : '#fff', color: tab === 'find' ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500 }}>Find Leads</button>
          <button onClick={() => { setTab('saved'); loadSaved(); }} style={{ padding: '6px 16px', fontSize: '0.85rem', borderRadius: '9999px', background: tab === 'saved' ? '#000' : '#fff', color: tab === 'saved' ? '#fff' : '#374151', border: '1px solid #e5e7eb', cursor: 'pointer', fontWeight: 500 }}>
            Saved ({savedLeads.length})
          </button>
        </div>
      </div>

      {tab === 'find' && (
        <>
          {/* Quick Presets */}
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>Quick Presets</h2>
            <p style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>One-click filters for common lead searches. You can edit the criteria after selecting.</p>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button onClick={() => {
                setActivePreset('german_startups');
                const preset = {
                  target_industries: ["internet", "computer software", "information technology"],
                  target_job_titles: ["Founder", "Co-Founder", "CEO", "CTO", "Managing Director", "Geschäftsführer"],
                  target_seniorities: ["founder", "owner", "c_suite"],
                  target_company_sizes: ["1,10"],
                  target_locations: ["Germany"],
                  target_keywords: "startup",
                  icp_description: "Early-stage startups and small companies in Germany with under 10 employees. Typically young companies that may need digital services.",
                  outreach_angle: "We noticed you're building something exciting. We help early-stage teams establish their online presence quickly and affordably."
                };
                setIcp(preset);

              }} style={{ padding: '8px 16px', fontSize: '0.8rem', background: activePreset === 'german_startups' ? '#000' : '#fff', color: activePreset === 'german_startups' ? '#fff' : '#374151', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer', transition: 'all 0.15s' }}>
                🇩🇪 German Startups (&lt;10 emp)
              </button>

              <button onClick={() => {
                setActivePreset('dach_ecommerce');
                const preset = {
                  target_industries: ["internet", "computer software", "e-commerce", "retail"],
                  target_job_titles: ["Founder", "CEO", "Head of Marketing", "Marketing Director", "CMO"],
                  target_seniorities: ["founder", "owner", "c_suite", "vp", "director"],
                  target_company_sizes: ["11,50"],
                  target_locations: ["Germany", "Austria", "Switzerland"],
                  target_keywords: "e-commerce OR online shop",
                  icp_description: "Small to mid-size e-commerce companies in DACH region looking to grow their online presence and customer engagement.",
                  outreach_angle: "We help e-commerce brands automate customer engagement across all channels with AI."
                };
                setIcp(preset);

              }} style={{ padding: '8px 16px', fontSize: '0.8rem', background: activePreset === 'dach_ecommerce' ? '#000' : '#fff', color: activePreset === 'dach_ecommerce' ? '#fff' : '#374151', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer', transition: 'all 0.15s' }}>
                🛒 DACH E-Commerce (11-50 emp)
              </button>

              <button onClick={() => {
                setActivePreset('german_agencies');
                const preset = {
                  target_industries: ["marketing and advertising", "design", "internet"],
                  target_job_titles: ["Founder", "CEO", "Creative Director", "Managing Director"],
                  target_seniorities: ["founder", "owner", "c_suite", "director"],
                  target_company_sizes: ["1,50"],
                  target_locations: ["Germany"],
                  target_keywords: "agency OR agentur",
                  icp_description: "Digital agencies and creative studios in Germany that may need AI-powered tools for their clients.",
                  outreach_angle: "We help agencies offer AI-powered customer engagement as a white-label service to their clients."
                };
                setIcp(preset);

              }} style={{ padding: '8px 16px', fontSize: '0.8rem', background: activePreset === 'german_agencies' ? '#000' : '#fff', color: activePreset === 'german_agencies' ? '#fff' : '#374151', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer', transition: 'all 0.15s' }}>
                🎨 German Digital Agencies
              </button>

              <button onClick={() => {
                setActivePreset('restaurants');
                const preset = {
                  target_industries: ["restaurants", "food and beverages", "hospitality"],
                  target_job_titles: ["Owner", "Founder", "Manager", "Geschäftsführer", "Inhaber"],
                  target_seniorities: ["founder", "owner", "manager"],
                  target_company_sizes: ["1,50"],
                  target_locations: ["Munich", "Berlin", "Hamburg", "Frankfurt", "Cologne"],
                  target_keywords: "restaurant OR cafe OR gastro",
                  icp_description: "Restaurants, cafes and food businesses in major German cities looking to improve their online ordering and customer communication.",
                  outreach_angle: "We help restaurants automate customer inquiries, reservations, and orders across Instagram, WhatsApp and more."
                };
                setIcp(preset);

              }} style={{ padding: '8px 16px', fontSize: '0.8rem', background: activePreset === 'restaurants' ? '#000' : '#fff', color: activePreset === 'restaurants' ? '#fff' : '#374151', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer', transition: 'all 0.15s' }}>
                🍽️ Restaurants in German Cities
              </button>
            </div>
          </div>

          {/* LinkedIn Direct Search */}
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>🔍 LinkedIn Search (via Unipile)</h2>
            <p style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>Search real LinkedIn profiles. Results include verified profile URLs.</p>
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
              <input type="text" value={linkedinKeywords} onChange={(e) => setLinkedinKeywords(e.target.value)}
                placeholder='e.g. "Founder startup Germany" or "CTO Berlin e-commerce"'
                onKeyDown={(e) => { if (e.key === 'Enter') searchLinkedIn(); }}
                style={{ flex: 1, padding: '8px 14px', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.875rem', outline: 'none' }} />
              <button onClick={searchLinkedIn} disabled={linkedinSearching || !linkedinKeywords}
                style={{ padding: '8px 20px', background: '#0077b5', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: 'pointer', opacity: (linkedinSearching || !linkedinKeywords) ? 0.5 : 1 }}>
                {linkedinSearching ? 'Searching...' : '🔍 Search LinkedIn'}</button>
            </div>

            {linkedinResults.length > 0 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <div style={{ fontSize: '0.8rem', color: '#6b7280' }}>{linkedinResults.length} people found</div>
                  <button
                    onClick={() => autoCallLinkedinLeads(linkedinResults)}
                    disabled={autoCalling}
                    style={{
                      padding: '6px 14px', fontSize: '0.75rem',
                      background: '#8b5cf6', color: '#fff',
                      border: 'none', borderRadius: '9999px', cursor: 'pointer',
                      opacity: autoCalling ? 0.5 : 1,
                    }}
                  >
                    {autoCalling ? '📞 Calling...' : '📞 Auto-Call All'}
                  </button>
                </div>
                {linkedinResults.map((person, i) => (
                  <div key={i} style={{ padding: '0.75rem 1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', marginBottom: '0.5rem', background: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                      {person.profile_picture && (
                        <img src={person.profile_picture} alt="" style={{ width: '40px', height: '40px', borderRadius: '50%', objectFit: 'cover' }} />
                      )}
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{person.first_name} {person.last_name}</div>
                        <div style={{ fontSize: '0.8rem', color: '#374151' }}>{person.headline}</div>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                          {person.company_name && `${person.company_name} · `}{person.location}
                          {person.network_distance && ` · ${person.network_distance}`}
                        </div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                      {person.linkedin_url && (
                        <a href={person.linkedin_url} target="_blank" rel="noopener noreferrer"
                          style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#0077b5', color: '#fff', borderRadius: '9999px', textDecoration: 'none' }}>Profile</a>
                      )}
                      <button onClick={() => sendInvite(person)}
                        style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>Connect</button>
                      <button onClick={() => { setSelectedLead(person); generateOutreach(person, 'linkedin_connection'); }}
                        style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>Draft</button>
                      <button onClick={() => saveLead({...person, ai_score: 0, ai_reason: '', ai_approach: ''})}
                        style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>Save</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Step 1: Select Persona + Generate ICP */}
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>1. Select Your Business Persona</h2>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <select value={selectedPersona} onChange={(e) => { setSelectedPersona(e.target.value); setIcp(null); setLeads([]); }}
                style={{ flex: 1, padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none' }}>
                <option value="">Select persona...</option>
                {personas.map(p => <option key={p.id} value={p.id}>{p.name} {p.company_name ? `(${p.company_name})` : ''}</option>)}
              </select>
              <button onClick={generateICP} disabled={!selectedPersona || loading}
                style={{ padding: '8px 20px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: loading ? 'wait' : 'pointer', opacity: (!selectedPersona || loading) ? 0.4 : 1, whiteSpace: 'nowrap' }}>
                {loading ? 'Analyzing...' : '🤖 Generate ICP'}
              </button>
            </div>
          </div>

          {/* Step 2: Editable Search Criteria */}
          {icp && (
            <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '0.75rem', padding: '1.5rem', marginBottom: '1.5rem' }}>
              <h2 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>2. Search Criteria</h2>
              <p style={{ fontSize: '0.8rem', color: '#1e40af', marginBottom: '1rem' }}>{icp.icp_description}</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>JOB TITLES (comma separated)</label>
                  <input type="text" value={(icp.target_job_titles || []).join(', ')}
                    onChange={(e) => setIcp({ ...icp, target_job_titles: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                    style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #bfdbfe', borderRadius: '0.375rem', outline: 'none', boxSizing: 'border-box' }} />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>SENIORITY LEVELS</label>
                  <input type="text" value={(icp.target_seniorities || []).join(', ')}
                    onChange={(e) => setIcp({ ...icp, target_seniorities: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                    style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #bfdbfe', borderRadius: '0.375rem', outline: 'none', boxSizing: 'border-box' }} />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>LOCATIONS</label>
                  <input type="text" value={(icp.target_locations || []).join(', ')}
                    onChange={(e) => setIcp({ ...icp, target_locations: e.target.value.split(',').map(s => s.trim()).filter(Boolean) })}
                    style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #bfdbfe', borderRadius: '0.375rem', outline: 'none', boxSizing: 'border-box' }} />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>COMPANY SIZE</label>
                  <select value={(icp.target_company_sizes || ["1,10"])[0]}
                    onChange={(e) => setIcp({ ...icp, target_company_sizes: [e.target.value] })}
                    style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #bfdbfe', borderRadius: '0.375rem', outline: 'none' }}>
                    <option value="1,10">1-10 employees</option>
                    <option value="11,50">11-50 employees</option>
                    <option value="51,200">51-200 employees</option>
                    <option value="201,500">201-500 employees</option>
                    <option value="501,1000">501-1000 employees</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>KEYWORDS</label>
                  <input type="text" value={icp.target_keywords || ''}
                    onChange={(e) => setIcp({ ...icp, target_keywords: e.target.value })}
                    style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #bfdbfe', borderRadius: '0.375rem', outline: 'none', boxSizing: 'border-box' }} />
                </div>
                <div>
                  <label style={{ fontSize: '0.7rem', color: '#6b7280', display: 'block', marginBottom: '3px' }}>VALUE PROPOSITION</label>
                  <input type="text" value={icp.outreach_angle || ''}
                    onChange={(e) => setIcp({ ...icp, outreach_angle: e.target.value })}
                    style={{ width: '100%', padding: '6px 10px', fontSize: '0.8rem', border: '1px solid #bfdbfe', borderRadius: '0.375rem', outline: 'none', boxSizing: 'border-box' }} />
                </div>
              </div>

              <button onClick={() => searchLeads(1)} disabled={searching}
                style={{ padding: '8px 24px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.875rem', cursor: searching ? 'wait' : 'pointer', opacity: searching ? 0.5 : 1 }}>
                {searching ? 'Searching the web...' : '🔍 Find Leads'}
              </button>
            </div>
          )}

          {/* Step 3: Lead Results */}
          {leads.length > 0 && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <h2 style={{ fontSize: '1rem', fontWeight: 600 }}>3. Results ({totalResults} found)</h2>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <button
                    onClick={() => autoCallLeads(leads.filter(l => (l.ai_score || 0) >= 70))}
                    disabled={autoCalling}
                    style={{
                      padding: '8px 16px', fontSize: '0.8rem',
                      background: '#8b5cf6', color: '#fff',
                      border: 'none', borderRadius: '9999px', cursor: 'pointer',
                      opacity: autoCalling ? 0.5 : 1,
                      display: 'flex', alignItems: 'center', gap: '6px',
                    }}
                  >
                    {autoCalling ? '📞 Calling...' : `📞 Auto-Call Top Leads (${leads.filter(l => (l.ai_score || 0) >= 70).length})`}
                  </button>
                  {page > 1 && <button onClick={() => searchLeads(page - 1)} style={{ padding: '4px 12px', fontSize: '0.75rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>← Prev</button>}
                  <span style={{ fontSize: '0.8rem', color: '#6b7280', padding: '4px 8px' }}>Page {page}</span>
                  <button onClick={() => searchLeads(page + 1)} style={{ padding: '4px 12px', fontSize: '0.75rem', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>Next →</button>
                </div>
              </div>

              {leads.map((lead, i) => (
                <div key={i} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', marginBottom: '0.5rem', background: '#fff' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '4px' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{lead.first_name} {lead.last_name}</span>
                        {lead.ai_score && (
                          <span style={{
                            fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px', fontWeight: 700,
                            background: lead.ai_score >= 80 ? '#d1fae5' : lead.ai_score >= 60 ? '#dbeafe' : lead.ai_score >= 40 ? '#fef3c7' : '#f3f4f6',
                            color: lead.ai_score >= 80 ? '#065f46' : lead.ai_score >= 60 ? '#1e40af' : lead.ai_score >= 40 ? '#92400e' : '#6b7280',
                          }}>{lead.ai_score}/100</span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.85rem', color: '#374151' }}>{lead.title}</div>
                      <div style={{ fontSize: '0.85rem', color: '#3b82f6', fontWeight: 500 }}>{lead.company_name}</div>
                      <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '2px' }}>
                        {[lead.company_industry, lead.company_size ? `${lead.company_size} emp` : '', lead.city, lead.country].filter(Boolean).join(' · ')}
                      </div>
                      {lead.ai_reason && (
                        <div style={{ fontSize: '0.8rem', color: '#059669', marginTop: '4px' }}>💡 {lead.ai_reason}</div>
                      )}
                      {lead.ai_approach && (
                        <div style={{ fontSize: '0.8rem', color: '#7c3aed', marginTop: '2px' }}>🎯 {lead.ai_approach}</div>
                      )}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginLeft: '1rem' }}>
                      <button onClick={() => saveLead(lead)}
                        style={{ padding: '4px 12px', fontSize: '0.7rem', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>💾 Save</button>
                      {lead.linkedin_url ? (
                        <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer"
                          style={{ padding: '4px 12px', fontSize: '0.7rem', background: '#0077b5', color: '#fff', borderRadius: '9999px', textDecoration: 'none', textAlign: 'center' }}>🔍 Find on LinkedIn</a>
                      ) : null}
                      <button onClick={() => { setSelectedLead(lead); generateOutreach(lead, 'email'); }}
                        style={{ padding: '4px 12px', fontSize: '0.7rem', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>✉️ Draft</button>
                    </div>
                  </div>
                </div>
              ))}

              {callResults.length > 0 && (
                <div style={{ marginTop: '1rem', padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', background: '#f9fafb' }}>
                  <h3 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>📞 Call Results</h3>
                  {callResults.map((r, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', fontSize: '0.8rem', borderBottom: '1px solid #f3f4f6' }}>
                      <span>{r.name} ({r.company})</span>
                      <span style={{
                        color: r.status === 'called' ? '#10b981' : r.status === 'linkedin_sent' ? '#0077b5' : '#ef4444',
                        fontWeight: 600,
                      }}>
                        {r.status === 'called' ? '✓ Call initiated' :
                         r.status === 'linkedin_sent' ? '✓ LinkedIn invite sent' :
                         r.status === 'no_phone' ? '→ LinkedIn invite sent (no phone)' :
                         `✗ ${r.error || 'Failed'}`}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Auto-Generated Landing Page */}
          {(generatingLP || autoLandingPage) && (
            <div style={{ marginTop: '1.5rem', background: '#fff', border: '2px solid #8b5cf6', borderRadius: '0.75rem', overflow: 'hidden' }}>
              <div style={{ padding: '1rem 1.25rem', background: '#f5f3ff', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#5b21b6', marginBottom: '2px' }}>
                    {generatingLP ? '🤖 Generating Landing Page...' : `🎨 Landing Page for ${autoLandingPage?.company}`}
                  </h3>
                  <p style={{ fontSize: '0.75rem', color: '#7c3aed' }}>
                    {generatingLP ? 'Clerque is creating a custom landing page for the top lead...' : 'Auto-generated based on the top-scored lead'}
                  </p>
                </div>
                {autoLandingPage && (
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button onClick={() => window.open(`/api/v1/landing-pages/${autoLandingPage.id}/preview`, '_blank')}
                      style={{ padding: '6px 14px', fontSize: '0.75rem', background: '#8b5cf6', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>↗ Full Preview</button>
                    <button onClick={() => {
                      const blob = new Blob([autoLandingPage.html], { type: 'text/html' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${autoLandingPage.company || 'landing-page'}.html`.replace(/\s+/g, '-').toLowerCase();
                      a.click();
                    }}
                      style={{ padding: '6px 14px', fontSize: '0.75rem', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>⬇ Download</button>
                    <button onClick={() => window.location.href = `/landing-pages`}
                      style={{ padding: '6px 14px', fontSize: '0.75rem', background: '#fff', color: '#374151', border: '1px solid #e5e7eb', borderRadius: '9999px', cursor: 'pointer' }}>✏️ Edit</button>
                  </div>
                )}
              </div>

              {generatingLP ? (
                <div style={{ padding: '3rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '2rem', marginBottom: '1rem', animation: 'spin 2s linear infinite' }}>🤖</div>
                  <div style={{ color: '#7c3aed', fontSize: '0.9rem' }}>Clerque is designing a custom landing page...</div>
                  <div style={{ color: '#9ca3af', fontSize: '0.8rem', marginTop: '0.5rem' }}>This takes about 15-20 seconds</div>
                  <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
                </div>
              ) : autoLandingPage ? (
                <iframe
                  srcDoc={autoLandingPage.html}
                  style={{ width: '100%', height: '500px', border: 'none' }}
                  title="Auto Landing Page Preview"
                />
              ) : null}
            </div>
          )}

          {/* Outreach Message Modal */}
          {selectedLead && (
            <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
              onClick={() => { setSelectedLead(null); setOutreachMsg(''); }}>
              <div onClick={(e) => e.stopPropagation()} style={{ background: '#fff', borderRadius: '0.75rem', padding: '1.5rem', width: '650px', maxHeight: '85vh', overflowY: 'auto' }}>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  Reach out to {selectedLead.first_name} {selectedLead.last_name}
                </h3>
                <p style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>{selectedLead.title} at {selectedLead.company_name}</p>

                {/* Channel buttons */}
                <div style={{ display: 'flex', gap: '6px', marginBottom: '1rem' }}>
                  <button onClick={() => generateOutreach(selectedLead, 'linkedin')} disabled={generatingMsg}
                    style={{ padding: '6px 14px', fontSize: '0.8rem', background: '#0077b5', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>
                    {generatingMsg ? '...' : '💼 LinkedIn Message'}</button>
                  <button onClick={() => generateOutreach(selectedLead, 'linkedin_connection')} disabled={generatingMsg}
                    style={{ padding: '6px 14px', fontSize: '0.8rem', background: '#0077b5', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer', opacity: 0.8 }}>
                    {generatingMsg ? '...' : '🤝 Connection Request Note'}</button>
                  <button onClick={() => generateOutreach(selectedLead, 'email')} disabled={generatingMsg}
                    style={{ padding: '6px 14px', fontSize: '0.8rem', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>
                    {generatingMsg ? '...' : '📧 Email'}</button>
                  <button onClick={() => generateOutreach(selectedLead, 'whatsapp')} disabled={generatingMsg}
                    style={{ padding: '6px 14px', fontSize: '0.8rem', background: '#25d366', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>
                    {generatingMsg ? '...' : '💬 WhatsApp'}</button>
                </div>

                {/* AI Reasoning */}
                {selectedLead.ai_reason && (
                  <div style={{ background: '#f0fdf4', padding: '0.75rem', borderRadius: '0.5rem', marginBottom: '1rem', fontSize: '0.8rem' }}>
                    <div style={{ color: '#059669', marginBottom: '4px' }}>💡 <strong>Why this lead:</strong> {selectedLead.ai_reason}</div>
                    <div style={{ color: '#7c3aed' }}>🎯 <strong>Approach:</strong> {selectedLead.ai_approach}</div>
                  </div>
                )}

                {/* Generated Message */}
                <textarea value={outreachMsg} onChange={(e) => setOutreachMsg(e.target.value)} rows={8}
                  placeholder="Click a channel button above to generate a message..."
                  style={{ width: '100%', padding: '12px', border: '1px solid #e5e7eb', borderRadius: '0.5rem', fontSize: '0.875rem', outline: 'none', resize: 'vertical', boxSizing: 'border-box', marginBottom: '0.75rem' }} />

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button onClick={() => { navigator.clipboard.writeText(outreachMsg); alert('Message copied! Now paste it on LinkedIn.'); }}
                    disabled={!outreachMsg}
                    style={{ padding: '8px 16px', background: '#000', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer', opacity: outreachMsg ? 1 : 0.4 }}>
                    📋 Copy Message</button>
                  {selectedLead.linkedin_url && (
                    <a href={selectedLead.linkedin_url} target="_blank" rel="noopener noreferrer"
                      style={{ padding: '8px 16px', background: '#0077b5', color: '#fff', borderRadius: '9999px', fontSize: '0.85rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
                      🔍 Find on LinkedIn</a>
                  )}
                  <button onClick={async () => {
                    await saveLead({ ...selectedLead, status: 'contacted' });
                    const saved = savedLeads.find(l => l.apollo_id === selectedLead.apollo_id);
                    if (saved) {
                      await fetch(`/api/v1/leads/saved/${saved.id}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ outreach_message: outreachMsg, status: 'contacted' }),
                      });
                    }
                    setSelectedLead(null);
                    setOutreachMsg('');
                    loadSaved();
                  }}
                    style={{ padding: '8px 16px', background: '#10b981', color: '#fff', border: 'none', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer' }}>
                    ✓ Save & Mark as Contacted</button>
                  <button onClick={() => { setSelectedLead(null); setOutreachMsg(''); }}
                    style={{ padding: '8px 16px', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '9999px', fontSize: '0.85rem', cursor: 'pointer' }}>Close</button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Saved Leads Tab */}
      {tab === 'saved' && (
        <div>
          {savedLeads.length === 0 ? (
            <div style={{ color: '#9ca3af', padding: '3rem', textAlign: 'center', border: '1px dashed #e5e7eb', borderRadius: '0.75rem' }}>
              No saved leads yet. Use "Find Leads" to discover potential customers.
            </div>
          ) : (
            savedLeads.map((lead) => (
              <div key={lead.id} style={{ padding: '1rem', border: '1px solid #e5e7eb', borderRadius: '0.75rem', marginBottom: '0.5rem', background: '#fff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{lead.first_name} {lead.last_name}</span>
                      <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px', fontWeight: 700,
                        background: lead.ai_score >= 80 ? '#d1fae5' : '#dbeafe',
                        color: lead.ai_score >= 80 ? '#065f46' : '#1e40af' }}>{lead.ai_score}/100</span>
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#374151' }}>{lead.title} at <strong>{lead.company_name}</strong></div>
                    <div style={{ fontSize: '0.8rem', color: '#059669', marginTop: '2px' }}>💡 {lead.ai_reason}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <select value={lead.status} onChange={(e) => updateLeadStatus(lead.id, e.target.value)}
                      style={{
                        padding: '4px 8px', fontSize: '0.7rem', borderRadius: '9999px', border: '1px solid #e5e7eb', outline: 'none', fontWeight: 600,
                        background: STATUS_OPTIONS.find(s => s.value === lead.status)?.color + '20',
                        color: STATUS_OPTIONS.find(s => s.value === lead.status)?.color,
                      }}>
                      {STATUS_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>
                    {lead.linkedin_url && <a href={lead.linkedin_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.7rem', color: '#0077b5' }}>🔍 Find on LinkedIn</a>}
                    {lead.phone && (
                      <button onClick={async () => {
                        if (!confirm(`Trigger AI phone call to ${lead.first_name} at ${lead.phone}?`)) return;
                        const resp = await fetch('/api/v1/happyrobot/call', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            phone_number: lead.phone,
                            customer_name: `${lead.first_name} ${lead.last_name}`,
                            context: `Lead from ${lead.company_name}. ${lead.ai_reason || ''}`,
                          }),
                        });
                        const data = await resp.json();
                        if (data.success) {
                          alert(`AI call initiated! Call ID: ${data.call_id}`);
                        } else {
                          alert(`Call failed: ${data.error}`);
                        }
                      }} style={{ padding: '4px 10px', fontSize: '0.7rem', background: '#8b5cf6', color: '#fff', border: 'none', borderRadius: '9999px', cursor: 'pointer' }}>📞 AI Call</button>
                    )}
                    <button onClick={() => deleteLead(lead.id)} style={{ fontSize: '0.7rem', color: '#dc2626', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
