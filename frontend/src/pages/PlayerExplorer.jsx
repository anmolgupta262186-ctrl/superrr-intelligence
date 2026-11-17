
import { useState } from "react";
import { Search, Users } from "lucide-react";

export default function PlayerExplorer({ players = [] }) {
    const [search, setSearch] = useState("");
    const [skill, setSkill] = useState("All");
    const [role, setRole] = useState("All");
    const [baseline, setBaseline] = useState("Normal");
    const [competition, setCompetition] = useState("All");

    const roles = [...new Set(
        players.map(p => p.target_role).filter(Boolean)
    )];

    const competitions = [...new Set(
        players.map(p => p.competition).filter(Boolean)
    )];

    const filtered = players.filter(p =>
        String(p.canonical_name || p.player_name || "")
            .toLowerCase().includes(search.toLowerCase()) &&
        (skill === "All" || p.skill === skill) &&
        (role === "All" || p.target_role === role) &&
        (competition === "All" || p.competition === competition) &&
        p.baseline_category === baseline
    ).sort((a, b) =>
        (b.final_rri ?? b.rri ?? 0) -
        (a.final_rri ?? a.rri ?? 0)
    );

    const fmt = v => v == null ? "N/A" : Number(v).toFixed(2);

    const inputStyle =
        "bg-[#111d33] border border-slate-700 rounded-xl p-3 outline-none w-full";

    return (
        <div className="space-y-6">

            <div className="bg-[#111d33] p-6 rounded-2xl">
                <div className="flex gap-3 items-center mb-5">
                    <Users className="text-pink-400" />
                    <h2 className="text-xl font-bold">
                        Global Talent Database
                    </h2>
                </div>

                <div className="grid md:grid-cols-2 xl:grid-cols-5 gap-4">

                    <input
                        className={inputStyle}
                        placeholder="Search player..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />

                    <select className={inputStyle} value={skill}
                        onChange={e => setSkill(e.target.value)}>
                        {["All", "Batting", "Bowling"].map(x =>
                            <option key={x}>{x}</option>
                        )}
                    </select>

                    <select className={inputStyle} value={role}
                        onChange={e => setRole(e.target.value)}>
                        {["All", ...roles].map(x =>
                            <option key={x}>{x}</option>
                        )}
                    </select>

                    <select className={inputStyle} value={competition}
                        onChange={e => setCompetition(e.target.value)}>
                        {["All", ...competitions].map(x =>
                            <option key={x}>{x}</option>
                        )}
                    </select>

                    <select className={inputStyle} value={baseline}
                        onChange={e => setBaseline(e.target.value)}>
                        <option>Normal</option>
                        <option>Moderate</option>
                    </select>

                </div>
            </div>

            <p className="text-slate-400">
                {filtered.length} matching performance records
            </p>

            <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5">

                {filtered.map((p, i) => {
                    const name = p.canonical_name || p.player_name;

                    return (
                        <div key={i}
                            className="bg-[#111d33] border border-slate-800 rounded-2xl p-5 hover:border-pink-500/50 transition">

                            <div className="flex gap-4 items-center">

                                <div className="w-14 h-14 shrink-0 rounded-full bg-pink-500/15 flex items-center justify-center text-pink-400 font-bold">
                                    {name?.split(" ").map(n => n[0]).slice(0, 2).join("")}
                                </div>

                                <div className="min-w-0">
                                    <h2 className="font-bold text-lg">{name}</h2>
                                    <p className="text-sm text-slate-400">
                                        {p.target_role}
                                    </p>
                                    <p className="text-xs text-slate-500">
                                        {p.competition}
                                    </p>
                                </div>

                            </div>

                            <div className="grid grid-cols-3 gap-2 mt-5">
                                {[
                                    ["PRI", p.pri],
                                    ["WHI", p.whi],
                                    ["RRI", p.final_rri ?? p.rri]
                                ].map(([label, value]) => (
                                    <div key={label}
                                        className="bg-[#080f20] rounded-xl p-3">
                                        <p className="text-xs text-slate-400">{label}</p>
                                        <p className="text-xl font-bold text-pink-400">
                                            {fmt(value)}
                                        </p>
                                    </div>
                                ))}
                            </div>

                            <div className="flex justify-between mt-5 text-sm">
                                <span className="text-slate-400">
                                    Pressure response
                                </span>
                                <span className={
                                    p.pressure_signal === "Positive"
                                        ? "text-emerald-400"
                                        : p.pressure_signal === "Negative"
                                            ? "text-red-400"
                                            : "text-yellow-400"
                                }>
                                    {p.pressure_signal || "Unknown"}
                                </span>
                            </div>

                            <p className="text-xs text-slate-500 mt-4">
                                Pressure balls: {p.balls_pressure ?? "N/A"}
                            </p>

                            <p className="text-xs text-amber-400 mt-2">
                                {p.selection_status || "Availability unverified"}
                            </p>

                        </div>
                    );
                })}

            </div>

            <p className="text-xs text-slate-500">
                Exploratory scouting database. Scores across competitions
                are not fully calibrated. Availability requires verification.
            </p>
        </div>
    );
}
