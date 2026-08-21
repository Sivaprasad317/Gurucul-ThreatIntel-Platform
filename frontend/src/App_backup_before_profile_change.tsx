import { useEffect, useMemo, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import { geoNaturalEarth1, geoPath } from "d3-geo";
import { feature } from "topojson-client";
import world from "world-atlas/countries-110m.json";

const API = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8002/api/v1";

type Actor = { id: string; name: string; slug: string; status: string; actor_type: string; victims: number };
type Overview = {
  actor: { id: string; name: string; slug: string; status: string; actor_type: string; description?: string; aliases?: string; first_observed_at?: string; discovery_date?: string };
  kpis: { victims:number; countries:number; industries:number; new_30d:number; first_victim:string|null; last_seen:string|null; avg_delay_days:number|null; uptime_30d:number|null };
  quality: { total:number; country_known:number; industry_known:number; published_known:number; description_known:number; country_coverage:number; industry_coverage:number; published_coverage:number; description_coverage:number };
  health: { status:string; crawls:number; completed_crawls:number; last_crawl:string|null; uptime_30d:number|null };
};
type Country = {code:string; name:string; count:number};
type Industry = {code:string; name:string; count:number};
type Activity = { velocity:{month:string;count:number}[]; monthly:{year:number;month:number;count:number}[]; cumulative:{month:string;count:number}[] };
type Victim = {id:string; name:string; country_code:string|null; country_name:string|null; industry_code:string|null; industry_name:string|null; description:string|null; published_on:string|null; discovered_on:string|null; source_page:string; first_seen_at:string; last_seen_at:string};
type Config = {demo_mode:boolean; live_api_configured:boolean};
type ActorProfile = {
  description: string;
  first_observed_at: string;
  discovery_date: string;
  aliases: string;
};
type ActorProfileMap = Record<string, ActorProfile>;

const EMPTY_ACTOR_PROFILE: ActorProfile = {
  description: "",
  first_observed_at: "",
  discovery_date: "",
  aliases: "",
};

function readActorProfiles(): ActorProfileMap {
  try {
    const raw = localStorage.getItem("gurucul_actor_profiles");
    return raw ? JSON.parse(raw) as ActorProfileMap : {};
  } catch {
    return {};
  }
}

async function request<T>(path:string, options:RequestInit={}) {
  const token = localStorage.getItem("gurucul_token");
  const res = await fetch(`${API}${path}`, {...options, headers:{...(token?{Authorization:`Bearer ${token}`}:{ }), "Content-Type":"application/json", ...(options.headers||{})}});
  if (!res.ok) {
    const body = await res.json().catch(()=>({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

function Icon({name}:{name:string}) {
  const common = {width:18,height:18,viewBox:"0 0 24 24",fill:"none",stroke:"currentColor",strokeWidth:1.8,strokeLinecap:"round" as const,strokeLinejoin:"round" as const};
  const paths:Record<string,ReactNode> = {
    dashboard:<><path d="M4 4h6v7H4z"/><path d="M14 4h6v4h-6z"/><path d="M14 12h6v8h-6z"/><path d="M4 15h6v5H4z"/></>,
    shield:<><path d="M12 3l7 3v5c0 5-3.2 8-7 10-3.8-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/></>,
    globe:<><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></>,
    activity:<><path d="M3 12h4l2-7 4 14 2-7h6"/></>,
    users:<><circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.2 2.4-5 6-5s6 1.8 6 5"/><circle cx="17" cy="9" r="2"/><path d="M17 14c2.4 0 4 1.4 4 4"/></>,
    database:<><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v7c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12v7c0 1.7 3.6 3 8 3s8-1.3 8-3v-7"/></>,
    refresh:<><path d="M20 11a8 8 0 0 0-14-4L4 9"/><path d="M4 4v5h5"/><path d="M4 13a8 8 0 0 0 14 4l2-2"/><path d="M20 20v-5h-5"/></>,
    search:<><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    x:<><path d="M6 6l12 12M18 6L6 18"/></>,
    external:<><path d="M14 4h6v6"/><path d="M20 4l-9 9"/><path d="M18 13v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h5"/></>,
    server:<><rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/><path d="M7 7h.01M7 17h.01"/></>,
    table:<><path d="M4 5h16M4 12h16M4 19h16M4 5v14M10 5v14M16 5v14"/></>,
  };
  return <svg {...common}>{paths[name] || paths.dashboard}</svg>;
}

function App() {
  const [token,setToken]=useState(localStorage.getItem("gurucul_token"));
  const [email,setEmail]=useState("admin@example.com");
  const [password,setPassword]=useState("ChangeMe123!");
  const [loginError,setLoginError]=useState("");
  const [actors,setActors]=useState<Actor[]>([]);
  const [actorId,setActorId]=useState("");
  const [overview,setOverview]=useState<Overview|null>(null);
  const [countries,setCountries]=useState<Country[]>([]);
  const [industries,setIndustries]=useState<Industry[]>([]);
  const [activity,setActivity]=useState<Activity>({velocity:[],monthly:[],cumulative:[]});
  const [victims,setVictims]=useState<Victim[]>([]);
  const [matrix,setMatrix]=useState<{rows:{country:string;industry:string;count:number}[]}>({rows:[]});
  const [config,setConfig]=useState<Config|null>(null);
  const [page,setPage]=useState<"dashboard"|"actors"|"victims"|"collection"|"system">("dashboard");
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(false);
  const [selectedVictim,setSelectedVictim]=useState<Victim|null>(null);
  const [search,setSearch]=useState("");
  const [countryFilter,setCountryFilter]=useState("");
  const [industryFilter,setIndustryFilter]=useState("");
  const [actorProfiles,setActorProfiles]=useState<ActorProfileMap>(() => readActorProfiles());

  useEffect(()=>{ if(token) void loadActors(); },[token]);

  async function loadActors() {
    try {
      const [a,c] = await Promise.all([request<Actor[]>("/dashboard/actors"),request<Config>("/config")]);
      setActors(a); setConfig(c);
      if(!actorId && a[0]) setActorId(a[0].id);
    } catch(e){ setError(e instanceof Error?e.message:"Unable to load actors."); }
  }

  useEffect(()=>{
    if(token && actorId) void loadActor(actorId);
  },[token,actorId]);

  async function loadVictimPage(
  groupId: string,
  offset = 0,
  limit = 100
): Promise<{ items: Victim[]; total: number | null }> {
  type VictimPage =
    | Victim[]
    | {
        items?: Victim[];
        victims?: Victim[];
        results?: Victim[];
        data?: Victim[];
        total?: number;
      };

  const response = await request<VictimPage>(
    `/dashboard/${encodeURIComponent(groupId)}/victims?offset=${offset}&limit=${limit}`
  );

  const items: Victim[] = Array.isArray(response)
    ? response
    : response.items ??
      response.victims ??
      response.results ??
      response.data ??
      [];

  if (!Array.isArray(items)) {
    throw new Error("Victim API returned an unexpected response format.");
  }

  const total =
    !Array.isArray(response) && typeof response.total === "number"
      ? response.total
      : null;

  return { items, total };
}


async function loadAllVictims(groupId: string): Promise<Victim[]> {
  const pageSize = 100;
  const maxPages = 20;
  const all: Victim[] = [];

  for (let pageNumber = 0; pageNumber < maxPages; pageNumber++) {
    const offset = pageNumber * pageSize;

    const { items, total } = await loadVictimPage(
      groupId,
      offset,
      pageSize
    );

    if (!items.length) {
      break;
    }

    all.push(...items);

    if (total !== null && all.length >= total) {
      break;
    }

    if (items.length < pageSize) {
      break;
    }

    /*
     * Prevent endless pagination if the backend ignores offset
     * and keeps returning the same records.
     */
    if (pageNumber > 0) {
      const previousPage = all.slice(
        all.length - items.length * 2,
        all.length - items.length
      );

      const previousIds = new Set(previousPage.map(v => v.id));

      if (
        items.length > 0 &&
        items.every(v => previousIds.has(v.id))
      ) {
        console.warn(
          `Stopping victim pagination because offset ${offset} returned duplicates.`
        );
        break;
      }
    }
  }

  return all;
}

  async function loadActor(id: string) {
  setLoading(true);
  setError("");

  try {
    const [o, c, i, a, v, m] = await Promise.all([
      request<Overview>(`/dashboard/${id}/overview`),
      request<Country[]>(`/dashboard/${id}/countries?limit=50`),
      request<Industry[]>(`/dashboard/${id}/industries?limit=50`),
      request<Activity>(`/dashboard/${id}/activity?months=12`),
      loadAllVictims(id),
      request<{ rows: { country: string; industry: string; count: number }[] }>(
        `/dashboard/${id}/matrix`
      ),
    ]);

    setOverview(o);
    setCountries(c);
    setIndustries(i);
    setActivity(a);
    setVictims(v);
    setMatrix(m);
  } catch (e) {
    setError(
      e instanceof Error
        ? e.message
        : "Unable to load actor dashboard."
    );
  } finally {
    setLoading(false);
  }
}

  async function login(ev: FormEvent) {
    ev.preventDefault();
    setLoginError("");

    try {
      const r = await request<{access_token: string}>("/auth/login", {
        method: "POST",
        body: JSON.stringify({email, password}),
      });

      localStorage.setItem("gurucul_token", r.access_token);
      setToken(r.access_token);
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : "Login failed.");
    }
  }

  function logout() {
    localStorage.removeItem("gurucul_token");
    setToken(null);
    setOverview(null);
    setVictims([]);
  }

  async function enrich() {
    if (!actorId) return;

    try {
      await request(`/dashboard/${actorId}/enrich`, {method: "POST"});

      setActorProfiles(prev => {
        const next = {...prev};
        delete next[actorId];

        localStorage.setItem(
          "gurucul_actor_profiles",
          JSON.stringify(next)
        );

        return next;
      });

      await loadActor(actorId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Profile update failed.");
    }
  }

  async function liveSync() {
    if (!actorId) return;

    try {
      await request(
        `/integrations/ransomware-live/groups/${actorId}/sync`,
        {method: "POST"}
      );
      await loadActor(actorId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Live sync failed.");
    }
  }

  function saveActorProfile(id: string, profile: ActorProfile) {
    setActorProfiles(prev => {
      const next = {...prev, [id]: profile};

      localStorage.setItem(
        "gurucul_actor_profiles",
        JSON.stringify(next)
      );

      return next;
    });
  }

  const filtered = useMemo(()=>victims.filter(v=>{
    const q=search.toLowerCase().trim();
    return (!q || [v.name,v.country_name,v.industry_name,v.description].filter(Boolean).join(" ").toLowerCase().includes(q))
      && (!countryFilter || v.country_code===countryFilter)
      && (!industryFilter || v.industry_code===industryFilter);
  }),[victims,search,countryFilter,industryFilter]);

  if(!token) return <Login email={email} setEmail={setEmail} password={password} setPassword={setPassword} error={loginError} onSubmit={login}/>;

  const actor=overview?.actor;
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><div className="text-brand"><strong>Gurucul</strong><span>THREATINTEL</span></div></div>
      <div className="side-label">INTELLIGENCE</div>
      <Nav active={page==="dashboard"} icon="dashboard" label="Actor Dashboard" onClick={()=>setPage("dashboard")}/>
      <Nav active={page==="actors"} icon="users" label="Threat Actors" onClick={()=>setPage("actors")}/>
      <Nav active={page==="victims"} icon="table" label="Victim Intelligence" onClick={()=>setPage("victims")}/>
      <div className="side-label">OPERATIONS</div>
      <Nav active={page==="collection"} icon="activity" label="Collection Health" onClick={()=>setPage("collection")}/>
      <Nav active={page==="system"} icon="server" label="System" onClick={()=>setPage("system")}/>
      <div className="side-spacer"/>
      <div className="side-health"><span className="status-dot"/> API operational</div>
      <button className="logout" onClick={logout}>Sign out</button>
    </aside>

    <main className="main">
      <header className="topbar">
        <div>
          <div className="crumb">THREAT INTELLIGENCE / ACTOR PROFILE</div>
        </div>

        <div className="top-actions">
          <label className="actor-switcher">
            <span>SWITCH ACTOR</span>
            <select value={actorId} onChange={e=>setActorId(e.target.value)}>
              {actors.map(a=><option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </label>

          {actor && <span className="pill active">{actor.status || "unknown"}</span>}
          {actor && <span className="pill type">{actor.actor_type || "Threat Actor"}</span>}
          {config?.demo_mode && <span className="demo-badge">DEMO DATA</span>}
          <button className="icon-button" onClick={()=>actorId&&loadActor(actorId)} title="Refresh"><Icon name="refresh"/></button>
          <div className="user-badge">AD</div>
        </div>
      </header>

      {error && <div className="error-banner">{error}<button onClick={()=>setError("")}><Icon name="x"/></button></div>}

      <div className="content">
        {page==="dashboard" && overview
          ? <Dashboard
              overview={overview}
              profile={actorProfiles[actorId]}
              countries={countries}
              industries={industries}
              activity={activity}
              matrix={matrix}
              victims={victims}
              onVictim={setSelectedVictim}
              onCountry={setCountryFilter}
              onIndustry={setIndustryFilter}
              onAllVictims={()=>setPage("victims")}
              enrich={enrich}
              liveSync={liveSync}
              config={config}
            />
          : page==="dashboard"
            ? <section className="panel dashboard-state">
                <div className="panel-body">
                  <h2>{loading ? "Loading actor intelligence…" : "Unable to load actor intelligence"}</h2>
                  <p>
                    {loading
                      ? "Loading the selected threat actor and its intelligence."
                      : error || "Select a threat actor or refresh the page."}
                  </p>
                  {!loading && actorId && (
                    <button
                      className="primary-button"
                      onClick={()=>loadActor(actorId)}
                    >
                      Retry
                    </button>
                  )}
                </div>
              </section>
            : null}
        {page==="actors" && <Actors actors={actors} current={actorId} onSelect={setActorId} profiles={actorProfiles} onSaveProfile={saveActorProfile}/>}
        {page==="victims" && <VictimPage victims={filtered} countries={countries} industries={industries} search={search} setSearch={setSearch} country={countryFilter} setCountry={setCountryFilter} industry={industryFilter} setIndustry={setIndustryFilter} onVictim={setSelectedVictim}/>}
        {page==="collection" && overview && <Collection overview={overview} actors={actors}/>}
        {page==="system" && <System config={config}/>}
      </div>
    </main>

    {loading && <div className="loading">Updating intelligence…</div>}
    {selectedVictim && <VictimDrawer victim={selectedVictim} close={()=>setSelectedVictim(null)}/>}
  </div>
}

function Login(p:{email:string;setEmail:(v:string)=>void;password:string;setPassword:(v:string)=>void;error:string;onSubmit:(e:FormEvent)=>void}) {
  return <div className="login"><form className="login-card" onSubmit={p.onSubmit}>
    <div className="text-brand login-brand"><strong>Gurucul</strong><span>THREATINTEL</span></div><div className="crumb">GURUCUL / THREAT INTELLIGENCE</div>
    <h1>Secure analyst access</h1><p>Actor-scoped ransomware intelligence and collection analytics.</p>
    <label>Email<input value={p.email} onChange={e=>p.setEmail(e.target.value)} type="email"/></label>
    <label>Password<input value={p.password} onChange={e=>p.setPassword(e.target.value)} type="password"/></label>
    {p.error&&<div className="error-inline">{p.error}</div>}
    <button className="primary-button">Sign in</button>
    <small>Local demo: admin@example.com / ChangeMe123!</small>
  </form></div>
}

function Nav(p:{active:boolean;icon:string;label:string;onClick:()=>void}){return <button className={`nav ${p.active?"active":""}`} onClick={p.onClick}><Icon name={p.icon}/>{p.label}</button>}

function Dashboard({overview,profile,countries,industries,activity,matrix,victims,onVictim,onCountry,onIndustry,onAllVictims,enrich,liveSync,config}:{overview:Overview;profile?:ActorProfile;countries:Country[];industries:Industry[];activity:Activity;matrix:{rows:{country:string;industry:string;count:number}[]};victims:Victim[];onVictim:(v:Victim)=>void;onCountry:(c:string)=>void;onIndustry:(i:string)=>void;onAllVictims:()=>void;enrich:()=>void;liveSync:()=>void;config:Config|null}) {
  const k=overview.kpis, q=overview.quality;
  const a={...overview.actor,...(profile||{})};
  return <div>
    <section className="actor-hero">
      <div className="actor-mark"><Icon name="shield"/></div>
      <div className="actor-hero-copy">
        <div className="hero-title-row"><h1>{a.name}</h1><span className="pill active">{a.status}</span><span className="pill type">{a.actor_type}</span></div>
        <p>{a.description || "No actor description has been collected."}</p>
        <div className="hero-meta">
          <span>First observed <b>{a.first_observed_at || "Unknown"}</b></span>
          <span>Discovery <b>{a.discovery_date || "Unknown"}</b></span>
          <span>Aliases <b>{a.aliases || "None recorded"}</b></span>
        </div>
      </div>
      <div className="hero-actions">
        <button className="secondary-button" onClick={enrich}>Update profile</button>
        {config?.live_api_configured && <button className="primary-button small" onClick={liveSync}>Sync live API</button>}
      </div>
    </section>

    {config?.demo_mode && <div className="notice"><b>DEMO DATA:</b> synthetic records are shown so you can validate the dashboard layout and actor-scoping. Replace them with live collection before using the intelligence operationally.</div>}

    <section className="kpi-grid">
      <Kpi label="Victims" value={fmt(k.victims)} icon="users" accent="green" note="Actor-scoped"/>
      <Kpi label="Countries" value={fmt(k.countries)} icon="globe" accent="cyan" note={`${q.country_coverage}% coverage`}/>
      <Kpi label="Industries" value={fmt(k.industries)} icon="table" accent="purple" note={`${q.industry_coverage}% coverage`}/>
      <Kpi label="First victim" value={dateOnly(k.first_victim)} icon="shield" accent="yellow" note="Earliest reliable date"/>
      <Kpi label="Last seen" value={dateOnly(k.last_seen)} icon="activity" accent="red" note={k.last_seen ? relative(k.last_seen) : "Unknown"}/>
      <Kpi label="New 30d" value={fmt(k.new_30d)} icon="activity" accent="green" note="Published/discovered"/>
      <Kpi label="Avg delay" value={k.avg_delay_days == null ? "—" : `${k.avg_delay_days}d`} icon="activity" accent="yellow" note="Discovered → published"/>
      <Kpi label="Collection" value={overview.health.status==="healthy"?"Healthy":"Pending"} icon="server" accent="cyan" note={overview.health.uptime_30d ? `${overview.health.uptime_30d}% / 30d` : "No completed crawl"}/>
    </section>

    <section className="grid-two">
      <Panel title="Attack velocity — last 12 months" meta="Uses published → discovered → first-seen fallback">
        <BarChart data={activity.velocity.map(x=>({label:x.month.slice(5),value:x.count}))}/>
      </Panel>
      <Panel title="Top countries" meta="Distinct normalized country codes">
        <RankBars items={countries.slice(0,10).map(x=>({label:x.name,sub:x.code,value:x.count}))} onClick={x=>onCountry(countries.find(c=>c.name===x)?.code || "")}/>
      </Panel>
    </section>

    <section className="grid-two">
      <Panel
  title="Geographic exposure"
  subtitle="Actor-scoped country distribution"
>
  <div className="geographic-layout">
    <TargetedCountries
      countries={countries}
      onCountry={onCountry}
    />

    <div className="geographic-map">
      <WorldMap
        countries={countries}
        onCountry={onCountry}
      />
    </div>
  </div>
</Panel>
      <Panel title="Top industries" meta="Controlled taxonomy; unknown values excluded">
        <RankBars items={industries.slice(0,10).map(x=>({label:x.name,value:x.count}))} onClick={x=>onIndustry(industries.find(i=>i.name===x)?.code || "")}/>
      </Panel>
    </section>

    <section className="grid-two">
      <Panel title="Victims per month" meta="Calendar months; source date precedence shown in tooltip">
        <MultiYearChart data={activity.monthly}/>
      </Panel>
      <Panel title="Cumulative victims" meta="Actor-scoped cumulative total">
        <LineChart data={activity.cumulative}/>
      </Panel>
    </section>

    <section className="grid-two">
      <Panel title="Country × industry targeting" meta="Only records with both fields populated">
        <Matrix rows={matrix.rows}/>
      </Panel>
      <Panel title="Data quality & coverage" meta="Missing metadata is not fabricated">
        <Coverage label="Country" value={q.country_coverage} detail={`${q.country_known} / ${q.total}`}/>
        <Coverage label="Industry" value={q.industry_coverage} detail={`${q.industry_known} / ${q.total}`}/>
        <Coverage label="Published date" value={q.published_coverage} detail={`${q.published_known} / ${q.total}`}/>
        <Coverage label="Description" value={q.description_coverage} detail={`${q.description_known} / ${q.total}`}/>
        <div className="quality-note">Enrichment retains field-level source and confidence. Unknown stays unknown.</div>
      </Panel>
    </section>

    <Panel title="Recently published victims" meta={`${victims.length} records loaded`} action={<button className="text-button" onClick={onAllVictims}>View all</button>}>
      <VictimTable victims={victims.slice(0,8)} onVictim={onVictim}/>
    </Panel>
  </div>
}

function Kpi({label,value,icon,accent,note}:{label:string;value: string | null;icon:string;accent:string;note:string}){return <div className={`kpi ${accent}`}><div className="kpi-icon"><Icon name={icon}/></div><div className="kpi-label">{label}</div><strong>{value}</strong><span>{note}</span></div>}
function Panel(p:{title:string;meta?:string;children:ReactNode;action?:ReactNode}){return <section className="panel"><div className="panel-head"><div><h2>{p.title}</h2>{p.meta&&<span>{p.meta}</span>}</div>{p.action}</div><div className="panel-body">{p.children}</div></section>}

function RankBars({items,onClick}:{items:{label:string;sub?:string;value:number}[];onClick?:(label:string)=>void}) {
  const max=Math.max(...items.map(x=>x.value),1);
  return <div className="rank-list">{items.map((x,i)=><button className="rank-row" key={x.label} onClick={()=>onClick?.(x.label)}><div className="rank-name"><span>{x.label}</span>{x.sub&&<em>{x.sub}</em>}</div><div className="rank-track"><i style={{width:`${x.value/max*100}%`}}/></div><b>{x.value}</b></button>)}</div>
}

function BarChart({data}:{data:{label:string;value:number}[]}) {
  const max=Math.max(...data.map(x=>x.value),1), h=210, w=760, gap=w/data.length;
  return <div className="chart-wrap"><svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="chart"><line x1="0" y1="175" x2={w} y2="175" className="gridline"/>{data.map((x,i)=>{const bh=(x.value/max)*145;return <g key={x.label}><rect x={i*gap+gap*.18} y={175-bh} width={gap*.64} height={bh} rx="4" className="bar"/><text x={i*gap+gap/2} y="198" textAnchor="middle">{x.label}</text></g>})}</svg></div>
}

function LineChart({data}:{data:{month:string;count:number}[]}) {
  if(!data.length)return <Empty text="No activity dates available."/>
  const max=Math.max(...data.map(x=>x.count),1), w=760,h=220;
  const pts=data.map((x,i)=>`${i*(w/(data.length-1||1))},${185-(x.count/max)*150}`).join(" ");
  return <div className="chart-wrap"><svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="chart"><line x1="0" y1="185" x2={w} y2="185" className="gridline"/><polyline points={pts} className="line"/>{data.map((x,i)=><circle key={x.month} cx={i*(w/(data.length-1||1))} cy={185-(x.count/max)*150} r="3" className="point"/>)}</svg><div className="chart-axis">{data.filter((_,i)=>i%2===0).map(x=><span key={x.month}>{x.month}</span>)}</div></div>
}

function MultiYearChart({data}:{data:{year:number;month:number;count:number}[]}) {
  const years=[...new Set(data.map(x=>x.year))].sort(), max=Math.max(...data.map(x=>x.count),1);
  return <div className="multi-chart">{years.slice(-4).map(year=><div className="year-series" key={year}><b>{year}</b><div className="month-bars">{Array.from({length:12},(_,idx)=>{const x=data.find(d=>d.year===year&&d.month===idx+1);return <div className="month-col" key={idx}><i style={{height:`${((x?.count||0)/max)*100}%`}} title={`${year}-${String(idx+1).padStart(2,"0")}: ${x?.count||0}`}/></div>})}</div></div>)}<div className="month-labels">{["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].map(x=><span key={x}>{x}</span>)}</div></div>
}

function TargetedCountries({
  countries,
  onCountry,
}: {
  countries: Country[];
  onCountry: (code: string) => void;
}) {
  const sortedCountries = [...countries].sort(
    (a, b) => b.count - a.count
  );

  return (
    <div className="targeted-countries">
      <div className="targeted-countries-header">
        <div>
          <div className="targeted-title">TARGETED COUNTRIES</div>
          <div className="targeted-subtitle">
            {sortedCountries.length} countries
          </div>
        </div>
      </div>

      <div className="targeted-table-header">
        <span>COUNTRY</span>
        <span>VICTIMS</span>
      </div>

      <div className="targeted-country-list">
        {sortedCountries.map((country) => (
          <button
            key={country.code}
            className="targeted-country-row"
            onClick={() => onCountry(country.code)}
            title={`Filter victims from ${country.name}`}
          >
            <span className="targeted-country-name">
              <span className={`country-flag flag-${country.code}`}>
                {country.code}
              </span>

              <span>{country.name}</span>
            </span>

            <strong>{country.count}</strong>
          </button>
        ))}
      </div>
    </div>
  );
}

function WorldMap({
  countries,
  onCountry,
}: {
  countries: Country[];
  onCountry: (code: string) => void;
}) {
  const width = 1200;
  const height = 560;

  const projection = useMemo(
    () =>
      geoNaturalEarth1()
        .scale(160)
        .translate([width / 2, height / 2 + 15]),
    []
  );

  const pathGenerator = useMemo(
    () => geoPath(projection),
    [projection]
  );

  const geo = useMemo(() => {
    return feature(
      world as never,
      (world as any).objects.countries
    ) as any;
  }, []);

  const countryCounts = useMemo(() => {
    const result = new Map<string, Country>();

    for (const country of countries) {
      result.set(country.name.toLowerCase().trim(), country);
    }

    return result;
  }, [countries]);

  const maxCount = Math.max(
    ...countries.map((country) => country.count),
    1
  );

  function getCountryData(featureItem: any): Country | undefined {
    const name =
      featureItem?.properties?.name ||
      featureItem?.properties?.NAME ||
      "";

    return countryCounts.get(name.toLowerCase().trim());
  }

  return (
    <div className="real-world-map">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="world-map-svg"
        role="img"
        aria-label="World map showing actor victim distribution"
      >
        <rect
          x="0"
          y="0"
          width={width}
          height={height}
          className="map-background"
        />

        {geo.features.map((countryFeature: any) => {
          const country = getCountryData(countryFeature);
          const count = country?.count ?? 0;

          const intensity =
            count > 0
              ? 0.18 + (count / maxCount) * 0.82
              : 0;

          const path = pathGenerator(countryFeature);

          if (!path) return null;

          return (
            <path
              key={countryFeature.id}
              d={path}
              className={`map-country ${
                country ? "map-country-active" : ""
              }`}
              style={
                {
                  "--map-intensity": intensity,
                } as CSSProperties
              }
              onClick={() => {
                if (country) {
                  onCountry(country.code);
                }
              }}
              title={
                country
                  ? `${country.name}: ${country.count} victims`
                  : countryFeature.properties?.name || "Unknown"
              }
            />
          );
        })}
      </svg>


    </div>
  );
}

function Matrix({rows}:{rows:{country:string;industry:string;count:number}[]}) {
  const countries=[...new Set(rows.map(r=>r.country))].slice(0,8), industries=[...new Set(rows.map(r=>r.industry))].slice(0,6);
  const val=(c:string,i:string)=>rows.find(r=>r.country===c&&r.industry===i)?.count||0;
  const max=Math.max(...rows.map(r=>r.count),1);
  if(!rows.length)return <Empty text="Not enough records have both country and industry metadata."/>
  return <div className="matrix-scroll"><table className="matrix"><thead><tr><th>Country</th>{industries.map(i=><th key={i}>{i}</th>)}</tr></thead><tbody>{countries.map(c=><tr key={c}><td>{c}</td>{industries.map(i=>{const n=val(c,i);return <td key={i} style={{background:`rgba(155,77,204,${n?0.08+(n/max)*0.42:0})`}}>{n||"—"}</td>})}</tr>)}</tbody></table></div>
}

function Coverage({label,value,detail}:{label:string;value:number;detail:string}){return <div className="coverage"><div><b>{label}</b><span>{detail}</span></div><div className="coverage-track"><i style={{width:`${value}%`}}/></div><strong>{value}%</strong></div>}

function VictimTable({victims,onVictim}:{victims:Victim[];onVictim:(v:Victim)=>void}) {
  if(!victims.length)return <Empty text="No victims match the current actor/filter."/>
  return <div className="victim-table"><div className="v-head"><span>Victim</span><span>Country</span><span>Industry</span><span>Published</span></div>{victims.map(v=><button className="v-row" key={v.id} onClick={()=>onVictim(v)}><strong>{v.name}</strong><span>{v.country_name||"Unknown"}</span><span>{v.industry_name||"Unknown"}</span><span>{dateOnly(v.published_on)||"Unknown"}</span></button>)}</div>
}

function VictimPage(p:{victims:Victim[];countries:Country[];industries:Industry[];search:string;setSearch:(v:string)=>void;country:string;setCountry:(v:string)=>void;industry:string;setIndustry:(v:string)=>void;onVictim:(v:Victim)=>void}) {
  return <div><div className="page-title"><div><div className="crumb">ACTOR-SCOPED INVENTORY</div><h1>Victim Intelligence</h1><p>Search and filter normalized records for the selected threat actor.</p></div></div><div className="filters"><div className="search"><Icon name="search"/><input value={p.search} onChange={e=>p.setSearch(e.target.value)} placeholder="Search victim, country, industry, description…"/></div><select value={p.country} onChange={e=>p.setCountry(e.target.value)}><option value="">All countries</option>{p.countries.map(c=><option key={c.code} value={c.code}>{c.name} ({c.count})</option>)}</select><select value={p.industry} onChange={e=>p.setIndustry(e.target.value)}><option value="">All industries</option>{p.industries.map(i=><option key={i.code} value={i.code}>{i.name} ({i.count})</option>)}</select></div><Panel title={`Victims · ${p.victims.length.toLocaleString()} loaded`} meta="All pages returned by the actor-scoped API are loaded; click a row for evidence and provenance"><VictimTable victims={p.victims} onVictim={p.onVictim}/></Panel></div>
}

function VictimDrawer({victim,close}:{victim:Victim;close:()=>void}) {
  return <div className="drawer-backdrop" onClick={close}><aside className="drawer" onClick={e=>e.stopPropagation()}><div className="drawer-top"><div><div className="crumb">VICTIM RECORD</div><h1>{victim.name}</h1></div><button className="icon-button" onClick={close}><Icon name="x"/></button></div><div className="drawer-grid"><Detail label="Country" value={victim.country_name}/><Detail label="Industry" value={victim.industry_name}/><Detail label="Published" value={dateOnly(victim.published_on)}/><Detail label="Discovered" value={dateOnly(victim.discovered_on)}/></div><div className="drawer-section"><h3>Description</h3><p>{victim.description||"No description extracted."}</p></div><div className="drawer-section"><h3>Evidence</h3><a href={victim.source_page} target="_blank" rel="noreferrer">{victim.source_page}<Icon name="external"/></a></div><div className="drawer-section"><h3>Enrichment policy</h3><p>Country and industry are actor-scoped normalized fields. Missing values remain unknown; enrichment should retain provenance and confidence.</p></div></aside></div>
}
function Detail({label,value}:{label:string;value:string|null|undefined}){return <div className="detail"><span>{label}</span><b>{value||"Unknown"}</b></div>}

function Actors({actors,current,onSelect,profiles,onSaveProfile}:{actors:Actor[];current:string;onSelect:(id:string)=>void;profiles:ActorProfileMap;onSaveProfile:(id:string,profile:ActorProfile)=>void}){
  const [name,setName]=useState("");
  const [slug,setSlug]=useState("");
  const [parser,setParser]=useState("dragonforce");
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState("");

  const selectedActor=actors.find(a=>a.id===current);
  const [profile,setProfile]=useState<ActorProfile>(EMPTY_ACTOR_PROFILE);

  useEffect(()=>{
    if(!current) {
      setProfile(EMPTY_ACTOR_PROFILE);
      return;
    }
    const saved=profiles[current];
    setProfile(saved || {
      description: "",
      first_observed_at: "",
      discovery_date: "",
      aliases: "",
    });
  },[current,profiles,actors]);

  async function create(){
    setBusy(true);
    setMessage("");
    try{
      const created=await request<Actor>("/groups",{
        method:"POST",
        body:JSON.stringify({name,slug,parser_key:parser,actor_type:"Ransomware",description:""})
      });
      setMessage(`Registered ${created.name}. Select it above to add its profile metadata.`);
      setName("");
      setSlug("");
    }catch(e){
      setMessage(e instanceof Error?e.message:"Unable to register actor.");
    }finally{
      setBusy(false);
    }
  }

  function updateProfile<K extends keyof ActorProfile>(key:K,value:ActorProfile[K]){
    setProfile(prev=>({...prev,[key]:value}));
  }

  function saveProfile(){
    if(!current || !selectedActor) return;
    onSaveProfile(current,profile);
    setMessage(`Profile metadata saved for ${selectedActor.name}.`);
  }

  return <div>
    <div className="page-title">
      <div>
        <div className="crumb">ACTOR INVENTORY</div>
        <h1>Threat Actors</h1>
        <p>Register actors and manually maintain the analyst-facing profile metadata.</p>
      </div>
    </div>

    <div className="register-panel">
      <div>
        <b>Register a threat actor</b>
        <span>Only installed actor-specific parsers can be registered.</span>
      </div>
      <input value={name} onChange={e=>setName(e.target.value)} placeholder="Actor name"/>
      <input value={slug} onChange={e=>setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g,"-"))} placeholder="slug"/>
      <select value={parser} onChange={e=>setParser(e.target.value)}>
        <option value="dragonforce">dragonforce</option>
        <option value="qilin">qilin</option>
        <option value="blackbasta">blackbasta</option>
      </select>
      <button className="primary-button" disabled={busy||!name||!slug} onClick={create}>Register</button>
    </div>

    {message&&<div className="notice">{message}</div>}

    <div className="actor-cards">
      {actors.map(a=>
        <button className={`actor-card ${a.id===current?"selected":""}`} key={a.id} onClick={()=>onSelect(a.id)}>
          <div className="actor-card-mark"><Icon name="shield"/></div>
          <div>
            <h2>{a.name}</h2>
            <span>{a.actor_type}</span>
            <small>{a.victims.toLocaleString()} actor-scoped victims</small>
          </div>
          <i>{a.status}</i>
        </button>
      )}
    </div>
  </div>
}
function Collection({overview,actors}:{overview:Overview;actors:Actor[]}){return <div><div className="page-title"><div><div className="crumb">OPERATIONS</div><h1>Collection Health</h1><p>Source availability is kept separate from threat-activity intelligence.</p></div></div><div className="grid-two"><Panel title={`${overview.actor.name} source health`} meta="30-day operational view"><div className="health-card"><div className="health-state"><span className="status-dot"/><strong>{overview.health.status}</strong></div><div className="health-metrics"><Detail label="Crawls" value={String(overview.health.crawls)}/><Detail label="Completed" value={String(overview.health.completed_crawls)}/><Detail label="Last crawl" value={dateOnly(overview.health.last_crawl)}/><Detail label="30d availability" value={overview.health.uptime_30d?`${overview.health.uptime_30d}%`:"—"}/></div></div></Panel><Panel title="Actor collection inventory" meta="Registered actors"><div className="collection-list">{actors.map(a=><div key={a.id}><span className="status-dot"/><b>{a.name}</b><em>{a.victims.toLocaleString()} victims</em></div>)}</div></Panel></div></div>}

function System({config}:{config:Config|null}){return <div><div className="page-title"><div><div className="crumb">PLATFORM</div><h1>System</h1><p>Configuration, data rules and deployment status.</p></div></div><div className="grid-two"><Panel title="Runtime"><Detail label="Mode" value={config?.demo_mode?"Demo":"Live"}/><Detail label="Ransomware.live" value={config?.live_api_configured?"Configured":"Not configured"}/><Detail label="Analytics" value="Server-side SQL aggregation"/><Detail label="Country model" value="ISO code + provenance"/><Detail label="Industry model" value="Controlled taxonomy + provenance"/></Panel><Panel title="Data rules"><div className="rules"><p><b>1.</b> All dashboard metrics are scoped to the selected actor.</p><p><b>2.</b> Country and industry counts exclude null/unknown values.</p><p><b>3.</b> Missing metadata is never replaced with fabricated values.</p><p><b>4.</b> Enrichment retains source and confidence.</p><p><b>5.</b> The frontend does not calculate intelligence totals.</p></div></Panel></div></div>}

function Empty({text}:{text:string}){return <div className="empty">{text}</div>}
function fmt(n:number){return n.toLocaleString()}
function dateOnly(v:string|null|undefined){if(!v)return null;return new Date(v).toLocaleDateString(undefined,{year:"numeric",month:"short",day:"2-digit"})}
function relative(v:string){const d=(Date.now()-new Date(v).getTime())/86400000;if(d<1)return "today";if(d<30)return `${Math.floor(d)}d ago`;return `${Math.floor(d/30)}mo ago`}

export default App;
