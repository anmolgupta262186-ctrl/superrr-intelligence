
import { useState } from "react";

import {
    BarChart, Bar, XAxis, YAxis,
    CartesianGrid, Tooltip, Legend,
    ResponsiveContainer
} from "recharts";

export default function PlayerComparison({ players = [] }) {

    const [skill, setSkill] = useState("Batting");
    const [baseline, setBaseline] = useState("Normal");
    const [first, setFirst] = useState("");
    const [second, setSecond] = useState("");

    const pool = players.filter(p =>
        p.skill === skill &&
        p.baseline_category === baseline
    );

    const label = p =>
        `${p.canonical_name || p.player_name} | ${p.competition} | ${p.phase} | ${p.target_role}`;

    const p1 = first === "" ? null : pool[Number(first)];
    const p2 = second === "" ? null : pool[Number(second)];

    const metrics = [
        ["PRI", "pri"],
        ["WHI", "whi"],
        ["RRI", "final_rri"]
    ];

    const chartData = p1 && p2
        ? metrics.map(([name, key]) => ({
            metric: name,
            Player1: p1[key] ?? null,
            Player2: p2[key] ?? null
        }))
        : [];

    const fmt = v =>
        v == null ? "N/A" : Number(v).toFixed(2);

    const style =
        "bg-[#080f20] border border-slate-700 rounded-xl p-3 w-full";

    function reset() {
        setFirst("");
        setSecond("");
    }

    function PlayerPanel({ p }) {

        const stats = skill === "Batting" ? [
            ["Baseline strike rate",
                p.sr_baseline ?? p.sr_normal],
            ["Pressure strike rate", p.sr_pressure],
            ["Baseline dismissal rate",
                p.dismissal_rate_baseline ?? p.dismissal_rate_normal],
            ["Pressure dismissal rate", p.dismissal_rate_pressure]
        ] : [
            ["Baseline run control",
                p.economy_baseline ?? p.run_rate_normal],
            ["Pressure run control",
                p.economy_pressure ?? p.run_rate_pressure],
            ["Baseline wicket rate",
                p.wicket_rate_baseline ?? p.wicket_rate_normal],
            ["Pressure wicket rate", p.wicket_rate_pressure]
        ];

        return (
            <div className="bg-[#111d33] rounded-2xl p-6">

                <h2 className="text-2xl font-bold">
                    {p.canonical_name || p.player_name}
                </h2>

                <p className="text-pink-400 mt-2">{p.target_role}</p>
                <p className="text-slate-400 text-sm">{p.competition}</p>

                <div className="space-y-4 mt-6">
                    {[
                        ...stats,
                        ["Pressure balls", p.balls_pressure],
                        ["Pressure matches", p.matches_pressure]
                    ].map(([name, value]) => (
                        <div key={name}
                            className="flex justify-between border-b border-slate-800 pb-3 gap-3">
                            <span className="text-slate-400">{name}</span>
                            <span className="font-bold">{fmt(value)}</span>
                        </div>
                    ))}
                </div>

                <p className="text-sm mt-5">
                    Pressure response: {p.pressure_signal || "Unknown"}
                </p>

                {skill === "Bowling" && (
                    <p className="text-xs text-slate-500 mt-3">
                        Run control metric: {p.economy_pressure != null
                            ? "Bowling economy"
                            : "Runs off bat per six legal balls"}
                    </p>
                )}

            </div>
        );
    }

    return (
        <div className="space-y-6">

            <div className="bg-[#111d33] p-6 rounded-2xl">

                <div className="grid md:grid-cols-2 gap-4 mb-5">

                    <select className={style} value={skill}
                        onChange={e => {
                            setSkill(e.target.value);
                            reset();
                        }}>
                        <option>Batting</option>
                        <option>Bowling</option>
                    </select>

                    <select className={style} value={baseline}
                        onChange={e => {
                            setBaseline(e.target.value);
                            reset();
                        }}>
                        <option>Normal</option>
                        <option>Moderate</option>
                    </select>

                </div>

                <div className="grid md:grid-cols-2 gap-4">

                    {[
                        [first, setFirst, "Select first player"],
                        [second, setSecond, "Select second player"]
                    ].map(([value, setter, title]) => (
                        <select key={title} className={style}
                            value={value}
                            onChange={e => setter(e.target.value)}>
                            <option value="">{title}</option>
                            {pool.map((p, i) => (
                                <option key={i} value={i}>{label(p)}</option>
                            ))}
                        </select>
                    ))}

                </div>
            </div>

            {p1 && p2 && (
                <>
                    <div className="grid md:grid-cols-2 gap-6">
                        <PlayerPanel p={p1} />
                        <PlayerPanel p={p2} />
                    </div>

                    <div className="bg-[#111d33] rounded-2xl p-6">

                        <h2 className="text-xl font-bold mb-6">
                            Recruitment Score Comparison
                        </h2>

                        <ResponsiveContainer width="100%" height={350}>
                            <BarChart data={chartData}>
                                <CartesianGrid
                                    stroke="#29364d"
                                    strokeDasharray="3 3"
                                />
                                <XAxis dataKey="metric" />
                                <YAxis domain={[0, 100]} />
                                <Tooltip contentStyle={{
                                    background: "#172544",
                                    border: "none"
                                }} />
                                <Legend />
                                <Bar
                                    dataKey="Player1"
                                    name={p1.canonical_name || p1.player_name}
                                    fill="#ea1a85"
                                    radius={[6, 6, 0, 0]}
                                />
                                <Bar
                                    dataKey="Player2"
                                    name={p2.canonical_name || p2.player_name}
                                    fill="#648be0"
                                    radius={[6, 6, 0, 0]}
                                />
                            </BarChart>
                        </ResponsiveContainer>

                    </div>

                    <p className="text-sm text-amber-400">
                        Comparisons across different competitions, phases,
                        roles and bowling metric definitions are descriptive,
                        not proof of superior ability.
                    </p>
                </>
            )}

        </div>
    );
}
