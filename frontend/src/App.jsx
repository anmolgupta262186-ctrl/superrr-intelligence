import AuctionSimulator from "./pages/AuctionSimulator";

import PlayerExplorer from "./pages/PlayerExplorer";
import PlayerComparison from "./pages/PlayerComparison";
import PressureAnalysis from "./pages/PressureAnalysis";
import Methodology from "./pages/Methodology";

import { useEffect, useState } from "react";

import {
  LayoutDashboard,
  ChartNoAxesCombined,
  Activity,
  Trophy,
  Target,
  Users,
  GitCompare,
  Wallet,
  BookOpen,
  Search,
  ArrowUpRight,
  Database,
  Menu,
  X,
} from "lucide-react";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

import {
  getBatters,
  getBowlers,
  getWeaknesses,
  getPlayers,
} from "./services/api";

const navigation = [
  ["Overview", LayoutDashboard],
  ["RR Weakness Analysis", ChartNoAxesCombined],
  ["Pressure Intelligence", Activity],
  ["Top 10 Batters", Trophy],
  ["Top 10 Bowlers", Target],
  ["Player Explorer", Users],
  ["Player Comparison", GitCompare],
  ["Auction Simulator", Wallet],
  ["Methodology", BookOpen],
];

function App() {
  const [active, setActive] = useState("Overview");
  const [sidebar, setSidebar] = useState(true);
  const [batters, setBatters] = useState([]);
  const [bowlers, setBowlers] = useState([]);
  const [weaknesses, setWeaknesses] = useState([]);
  const [players, setPlayers] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        const [bat, bowl, gaps, pool] =
          await Promise.all([
            getBatters(),
            getBowlers(),
            getWeaknesses(),
            getPlayers(),
          ]);

        setBatters(bat.data);
        setBowlers(bowl.data);
        setWeaknesses(gaps.data);
        setPlayers(pool.data);
      } catch (err) {
        setError("Unable to connect to analytics API.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const uniquePlayers = [
    ...new Set(
      players.map(
        (p) => p.canonical_name || p.player_name
      ).filter(Boolean)
    ),
  ].length;

  const metrics = [
    {
      title: "Scouted Players",
      value: uniquePlayers,
      icon: Users,
    },
    {
      title: "Ranked Batters",
      value: batters.length,
      icon: Trophy,
    },
    {
      title: "Ranked Bowlers",
      value: bowlers.length,
      icon: Target,
    },
    {
      title: "SMAT Matches",
      value: 695,
      icon: Database,
    },
  ];


  function RankingTable({ data, type }) {
    const batting = type === "batting";

    const number = (v) =>
      v == null || !Number.isFinite(Number(v))
        ? "N/A"
        : Number(v).toFixed(2);

    const section = "text-pink-400 text-xs font-bold uppercase tracking-widest mb-3";

    const flags = {
      India: "india",
      England: "england",
      Australia: "australia",
      "New Zealand": "new-zealand",
      USA: "usa",
      Zimbabwe: "zimbabwe",
      "Sri Lanka": "sri-lanka"
    };

    const filtered = data.filter(p =>
      String(p.player_name || "")
        .toLowerCase().includes(search.toLowerCase())
    );

    return (
      <div className="space-y-5">

        <p className="text-xs text-slate-400">
          Provisional recruitment shortlist.
          Auction eligibility and registration require verification.
          Ratings are not calibrated across competitions.
        </p>

        {filtered.length === 0 && (
          <p className="text-slate-400">
            No matching players.
          </p>
        )}

        {filtered.map(p => {

          
          const baselineRuns =
            p.runs_baseline ?? p.runs_normal;

          const baselineBalls =
            p.balls_baseline ?? p.balls_normal;

          const baselineDismissals =
            p.dismissals_baseline ?? p.dismissals_normal;

          const baselineWickets =
            p.wickets_baseline ?? p.wickets_normal;

          const baselineMatches =
            p.matches_baseline ?? p.matches_normal;

          const ratio = (a, b) =>
            a != null && b != null && Number(b) > 0
              ? Number(a) / Number(b)
              : null;

          const metric = (name, baseline, pressure) => ({
            name, baseline, pressure
          });

          const fullEconomy = p.economy_pressure != null;

          const stats = batting ? [

            metric("Runs scored",
              baselineRuns, p.runs_pressure),

            metric("Balls faced",
              baselineBalls, p.balls_pressure),

            metric("Strike rate",
              p.sr_baseline ?? p.sr_normal,
              p.sr_pressure),

            metric("Batting average",
              ratio(baselineRuns, baselineDismissals),
              ratio(p.runs_pressure, p.dismissals_pressure)),

            metric("Dismissals",
              baselineDismissals, p.dismissals_pressure),

            metric("Boundaries",
              p.boundaries_baseline, p.boundaries_pressure),

            metric("Boundary percentage",
              p.boundary_pct_baseline, p.boundary_pct_pressure),

            metric("Dot balls",
              p.dots_baseline, p.dots_pressure),

            metric("Dot-ball percentage",
              p.dot_pct_baseline, p.dot_pct_pressure),

            metric("Dismissals per 100 balls",
              p.dismissal_rate_baseline ?? p.dismissal_rate_normal,
              p.dismissal_rate_pressure),

            metric("Matches",
              baselineMatches, p.matches_pressure)

          ] : [

            metric("Wickets taken",
              baselineWickets, p.wickets_pressure),

            metric(fullEconomy
              ? "Runs conceded" : "Runs off the bat",
              baselineRuns, p.runs_pressure),

            metric("Legal balls bowled",
              baselineBalls, p.balls_pressure),

            metric(fullEconomy
              ? "Economy rate" : "Off-bat run rate",
              p.economy_baseline ?? p.run_rate_normal,
              p.economy_pressure ?? p.run_rate_pressure),

            metric(fullEconomy
              ? "Bowling average" : "Off-bat runs per wicket",
              ratio(baselineRuns, baselineWickets),
              ratio(p.runs_pressure, p.wickets_pressure)),

            metric("Bowling strike rate",
              ratio(baselineBalls, baselineWickets),
              ratio(p.balls_pressure, p.wickets_pressure)),

            metric("Wickets per 100 balls",
              p.wicket_rate_baseline ?? p.wicket_rate_normal,
              p.wicket_rate_pressure),

            metric("Dot balls",
              p.dots_baseline, p.dots_pressure),

            metric("Dot-ball percentage",
              p.dot_pct_baseline, p.dot_pct_pressure),

            metric("Matches",
              baselineMatches, p.matches_pressure)

          ];

          const highlights = batting ? [
            ["Pressure runs", p.runs_pressure],
            ["Balls faced", p.balls_pressure],
            ["Strike rate", p.sr_pressure],
            ["Batting average",
              ratio(p.runs_pressure, p.dismissals_pressure)],
            ["Boundaries", p.boundaries_pressure],
            ["Pressure matches", p.matches_pressure]
          ] : [
            ["Pressure wickets", p.wickets_pressure],
            [fullEconomy ? "Economy" : "Off-bat run rate",
              p.economy_pressure ?? p.run_rate_pressure],
            [fullEconomy ? "Runs conceded" : "Runs off bat",
              p.runs_pressure],
            ["Legal balls", p.balls_pressure],
            ["Bowling strike rate",
              ratio(p.balls_pressure, p.wickets_pressure)],
            ["Pressure matches", p.matches_pressure]
          ];

          const chartStats = stats.filter(s =>
            batting
              ? s.name === "Strike rate"
              : s.name === "Economy rate"
                || s.name === "Off-bat run rate"
          );

          return (
            <details
              key={`${type}-${p.rank}`}
              className="group bg-[#151f35] rounded-2xl border border-slate-700 overflow-hidden"
            >
              <summary className="cursor-pointer list-none flex items-center gap-4 p-5 hover:bg-white/5">

                <span className="text-pink-400 text-lg font-bold">
                  #{p.rank}
                </span>

                <div className="w-20 h-20 rounded-full overflow-hidden bg-pink-500/15 flex items-center justify-center text-pink-400 font-bold">
                  <img
  src={`/players/${p.player_name.toLowerCase().replaceAll(" ", "-")}.jpg`}
  alt={p.player_name}
  className="w-full h-full object-cover rounded-full"
  onError={(e) => {
    e.currentTarget.style.display = "none";
    e.currentTarget.nextElementSibling.style.display = "block";
  }}
/>
<span style={{display: "none"}}>
  {p.player_name.split(" ").map(n => n[0]).slice(0,2).join("")}
</span>
                </div>

                <div className="flex-1">
                  <h2 className="text-lg font-bold">
                    {p.player_name}
                  </h2>
                  <p className="text-xs text-slate-400">
                    <img
      src={`/flags/${flags[p.nationality]}.png`}
      alt={p.nationality}
      className="inline-block w-6 h-4 object-cover rounded-sm mr-2"
    /> {p.nationality}
                    {" · "}{p.role}
                  </p>
                </div>

                <div className="text-right">
                  <h2 className="text-2xl font-black text-pink-400">
                    {number(p.frs)}
                  </h2>
                  <p className="text-xs text-slate-400">
                    Rating / 100
                  </p>
                </div>

                <span className="text-slate-400 group-open:rotate-90">
                  ›
                </span>

              </summary>

              <div className="p-6 border-t border-slate-700 space-y-7">

                <section>
                  <h3 className={section}>01. Rating</h3>

                  {[
                    ["Pressure Reliability Index", p.pri],
                    ["Weakness Handling Index", p.whi],
                    ["Squad Priority", p.squad_priority],
                    ["Final Recruitment Score", p.frs]
                  ].map(([label, value]) => (
                    <div key={label} className="mb-4">
                      <div className="flex justify-between text-sm mb-2">
                        <span>{label}</span>
                        <span className="text-pink-400">
                          {number(value)}
                        </span>
                      </div>
                      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-pink-500 rounded-full"
                          style={{
                            width: `${Math.max(0, Math.min(100, Number(value) || 0))}%`
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </section>

                <section>
                  <h3 className={section}>02. Nationality</h3>
                  <p className="text-lg">
                    <img
      src={`/flags/${flags[p.nationality]}.png`}
      alt={p.nationality}
      className="inline-block w-6 h-4 object-cover rounded-sm mr-2"
    /> {p.nationality}
                  </p>
                  <p className="text-sm text-slate-400">
                    {p.overseas ? "Overseas slot" : "Indian player slot"}
                  </p>
                </section>

                <section>
                  <h3 className={section}>03. Role</h3>
                  <p className="font-semibold">{p.role}</p>
                  <p className="text-sm text-slate-400 mt-1">
                    Phase: {p.phase}
                  </p>
                </section>

                <section>
                  <h3 className={section}>04. Potential Impact</h3>
                  <p className="text-slate-300">{p.impact}</p>
                </section>

                <section>
                  <h3 className={section}>
                    05. Pressure Condition Handling
                  </h3>

                  <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4">
                    <p className="text-emerald-400 font-bold">
                      {p.pressure_signal} pressure response
                    </p>
                    <p className="text-sm text-slate-400 mt-2">
                      {p.baseline_category} vs High pressure
                    </p>
                    <p className="text-sm text-slate-400">
                      Evidence: {p.competition}
                    </p>
                  </div>
                </section>

                <section>
                  <h3 className={section}>
                    06. Pressure Condition Statistics
                  </h3>

                  
                  <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
                    {highlights.map(([label, value]) => (
                      <div key={label}
                        className="bg-[#0b1428] border border-slate-700 rounded-xl p-5">

                        <p className="text-xs text-slate-400">
                          {label}
                        </p>

                        <h2 className="text-3xl font-black text-pink-400 mt-3">
                          {value == null ? "N/A"
                            : Number.isInteger(Number(value))
                            ? Number(value).toLocaleString()
                            : number(value)}
                        </h2>

                      </div>
                    ))}
                  </div>

                  <p className="text-sm text-slate-400 mb-5">
                    Evidence: {p.competition} · {p.phase} overs
                    {" · "}{p.baseline_category} vs High pressure
                  </p>

                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={chartStats}>
                      <CartesianGrid
                        stroke="#29364d"
                        strokeDasharray="3 3"
                      />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: "#94a3b8", fontSize: 11 }}
                      />
                      <YAxis tick={{ fill: "#94a3b8" }} />
                      <Tooltip
                        contentStyle={{
                          background: "#172544",
                          border: "none"
                        }}
                      />
                      <Bar
                        dataKey="baseline"
                        name={p.baseline_category}
                        fill="#648be0"
                        radius={[5,5,0,0]}
                      />
                      <Bar
                        dataKey="pressure"
                        name="High pressure"
                        fill="#ea1a85"
                        radius={[5,5,0,0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>

                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-slate-400">
                        <tr>
                          <th className="py-3">Metric</th>
                          <th>{p.baseline_category}</th>
                          <th>High pressure</th>
                        </tr>
                      </thead>
                      <tbody>
                        {stats.map(s => (
                          <tr key={s.name} className="border-t border-slate-700">
                            <td className="py-3">{s.name}</td>
                            <td>{number(s.baseline)}</td>
                            <td className="text-pink-400">
                              {number(s.pressure)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mt-5">
                    {[
                      ["Pressure balls", p.balls_pressure],
                      ["Pressure matches", p.matches_pressure]
                    ].map(([label,value]) => (
                      <div key={label} className="bg-[#0e1930] p-4 rounded-xl">
                        <p className="text-xs text-slate-400">
                          {label}
                        </p>
                        <h3 className="text-2xl font-bold mt-2">
                          {value ?? "N/A"}
                        </h3>
                      </div>
                    ))}
                  </div>

                </section>

                <p className="text-xs text-amber-400">
                  {p.auction_status || "Availability pending"}
                  {" · "}Auction registration unverified
                </p>

              </div>
            </details>
          );
        })}
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[#080f20]">

      {sidebar && (
        <aside className="fixed inset-y-0 left-0 w-64 bg-[#0e1930] border-r border-slate-800 flex flex-col z-20">

          <div className="p-6 border-b border-slate-800">
            <h1 className="text-2xl font-black text-pink-500">
              SupeRR
            </h1>

            <h2 className="text-xl font-bold">
              INTELLIGENCE
            </h2>

            <p className="text-xs text-slate-400 mt-2 tracking-widest">
              CRICKET ANALYTICS
            </p>
          </div>

          <nav className="p-3 space-y-2 flex-1 overflow-y-auto">
            {navigation.map(([name, Icon]) => (
              <button
                key={name}
                onClick={() => {
                  setActive(name);
                  setSearch("");
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition ${active === name
                  ? "bg-pink-600/20 text-pink-400 border border-pink-500/20"
                  : "text-slate-400 hover:bg-white/5"
                  }`}
              >
                <Icon size={18} />
                {name}
              </button>
            ))}
          </nav>

          <div className="p-5 border-t border-slate-800">
            <p className="text-sm font-semibold">
              Rajasthan Royals
            </p>
            <p className="text-xs text-slate-500">
              Recruitment Intelligence Project
            </p>
          </div>
        </aside>
      )}

      <main className={`flex-1 min-w-0 ${sidebar ? "md:ml-64" : ""
        }`}>

        <header className="sticky top-0 z-10 bg-[#080f20]/95 border-b border-slate-800 px-6 py-4 flex items-center justify-between">

          <button onClick={() => setSidebar(!sidebar)}>
            {sidebar ? <X size={22} /> : <Menu size={22} />}
          </button>

          <div className="flex items-center gap-3 bg-[#131e34] rounded-xl px-4 py-2">
            <Search size={18} className="text-slate-400" />

            <input
              placeholder="Search players..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-transparent outline-none text-sm w-36 md:w-56"
            />
          </div>

          <span className="text-xs text-slate-400">
            IPL 2027
          </span>
        </header>

        <div className="p-6 md:p-8">

          <p className="text-pink-400 text-xs tracking-widest uppercase">
            Rajasthan Royals / Analytics
          </p>

          <h1 className="text-4xl font-bold mt-3 mb-3">
            {active === "Overview"
              ? "Recruitment Command Center"
              : active}
          </h1>

          <p className="text-slate-400 mb-8">
            Data-driven player evaluation and pressure intelligence.
          </p>

          {loading && <p>Loading analytics...</p>}

          {error && (
            <p className="text-red-400">{error}</p>
          )}

          {!loading && !error && active === "Overview" && (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">

                {metrics.map(({ title, value, icon: Icon }) => (
                  <div
                    key={title}
                    className="bg-[#111d33] border border-slate-800 rounded-2xl p-6"
                  >
                    <div className="flex justify-between">
                      <Icon className="text-pink-400" />
                      <ArrowUpRight
                        size={18}
                        className="text-slate-500"
                      />
                    </div>

                    <p className="text-slate-400 text-sm mt-5">
                      {title}
                    </p>

                    <h2 className="text-4xl font-bold mt-2">
                      {value}
                    </h2>
                  </div>
                ))}

              </div>

              <section className="bg-[#111d33] border border-slate-800 rounded-2xl p-6 mt-8">

                <h2 className="text-xl font-bold mb-6">
                  RR Recruitment Priorities
                </h2>

                <ResponsiveContainer width="100%" height={350}>
                  <BarChart
                    data={weaknesses.slice(0, 8)}
                    layout="vertical"
                    margin={{ left: 35, right: 20 }}
                  >
                    <CartesianGrid
                      stroke="#26334a"
                      strokeDasharray="3 3"
                    />
                    <XAxis type="number" domain={[0, 100]} />
                    <YAxis
                      type="category"
                      dataKey="role"
                      width={125}
                      tick={{ fill: "#94a3b8", fontSize: 11 }}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#172544",
                        border: "none",
                      }}
                    />
                    <Bar
                      dataKey="updated_priority"
                      fill="#EA1A85"
                      radius={[0, 6, 6, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>

              </section>

              <div className="grid xl:grid-cols-2 gap-6 mt-8">

                <section className="bg-[#111d33] border border-slate-800 rounded-2xl p-4">
                  <h2 className="text-xl font-bold p-3">
                    Leading Pressure Batters
                  </h2>
                  <RankingTable
                    data={batters.slice(0, 5)}
                    type="batting"
                  />
                </section>

                <section className="bg-[#111d33] border border-slate-800 rounded-2xl p-4">
                  <h2 className="text-xl font-bold p-3">
                    Leading Pressure Bowlers
                  </h2>
                  <RankingTable
                    data={bowlers.slice(0, 5)}
                    type="bowling"
                  />
                </section>

              </div>

              <p className="text-xs text-slate-500 mt-6">
                Recruitment rankings are provisional and subject to auction eligibility verification.
              </p>
            </>
          )}

          {!loading && !error && active === "Top 10 Batters" && (
            <section className="bg-[#111d33] rounded-2xl p-5">
              <RankingTable data={batters} type="batting" />
            </section>
          )}

          {!loading && !error && active === "Top 10 Bowlers" && (
            <section className="bg-[#111d33] rounded-2xl p-5">
              <RankingTable data={bowlers} type="bowling" />
            </section>
          )}

          {!loading && !error && active === "RR Weakness Analysis" && (
            <div className="space-y-4">
              {weaknesses.map((w) => (
                <div
                  key={w.role}
                  className="bg-[#111d33] rounded-xl p-5"
                >
                  <div className="flex justify-between mb-3">
                    <h3 className="font-semibold">{w.role}</h3>
                    <span className="text-pink-400">
                      {w.updated_priority}/100
                    </span>
                  </div>

                  <div className="bg-slate-800 h-2 rounded-full">
                    <div
                      className="bg-pink-500 h-2 rounded-full"
                      style={{ width: `${w.updated_priority}%` }}
                    />
                  </div>

                  <p className="text-slate-400 text-sm mt-3">
                    {w.reason}
                  </p>
                </div>
              ))}
            </div>
          )}


          {!loading && !error && active === "Pressure Intelligence" && (
            <PressureAnalysis />
          )}

          {!loading && !error && active === "Methodology" && (
            <Methodology />
          )}


          {!loading && !error && active === "Player Explorer" && (
            <PlayerExplorer players={players} />
          )}

          {!loading && !error && active === "Player Comparison" && (
            <PlayerComparison players={players} />
          )}


          {!loading && !error && active === "Auction Simulator" && (
            <AuctionSimulator
              batters={batters}
              bowlers={bowlers}
            />
          )}

          {![
            "Overview",
            "Top 10 Batters",
            "Top 10 Bowlers",
            "RR Weakness Analysis",
            "Pressure Intelligence",
            "Methodology",
            "Player Explorer",
            "Player Comparison",
          "Auction Simulator",
          ].includes(active) && (
              <div className="bg-[#111d33] rounded-2xl p-8">
                <h2 className="text-xl font-bold">
                  {active}
                </h2>
                <p className="text-slate-400 mt-3">
                  Module under development.
                </p>
              </div>
            )}

        </div>
      </main>
    </div>
  );
}

export default App;
