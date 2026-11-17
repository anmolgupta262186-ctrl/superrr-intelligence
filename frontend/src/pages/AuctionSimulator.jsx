
import { useState } from "react";
import {
    Wallet, Users, Globe, Trash2,
    RotateCcw, ShoppingCart
} from "lucide-react";

export default function AuctionSimulator({
    batters = [],
    bowlers = []
}) {

    const TOTAL_BUDGET = 2705; // Lakhs
    const MAX_SLOTS = 6;
    const MAX_OVERSEAS = 3;

    const [squad, setSquad] = useState([]);
    const [selected, setSelected] = useState("");
    const [bid, setBid] = useState("");
    const [error, setError] = useState("");
    const [search, setSearch] = useState("");

    const players = [...new Map(
        [...batters, ...bowlers].map(p => [
            p.player_name, p
        ])
    ).values()].filter(p => p.player_name);

    const spent = squad.reduce(
        (sum, p) => sum + p.price, 0
    );

    const remaining = TOTAL_BUDGET - spent;

    const overseas = squad.filter(
        p => p.overseas
    ).length;

    const indian = squad.length - overseas;

    const available = players.filter(p =>
        !squad.some(s => s.player_name === p.player_name)
    );

    const player = available.find(
        p => p.player_name === selected
    );

    const money = value =>
        `₹${(value / 100).toFixed(2)} Cr`;

    function purchase() {
        setError("");

        const price = Math.round(Number(bid) * 100);

        if (!player)
            return setError("Select a player first.");

        if (!player.nationality ||
            typeof player.overseas !== "boolean")
            return setError("Player nationality requires verification.");

        if (!Number.isFinite(price) || price <= 0)
            return setError("Enter a valid bid amount.");

        if (price > remaining)
            return setError("Insufficient auction budget.");

        if (squad.length >= MAX_SLOTS)
            return setError("All squad slots are occupied.");

        if (player.overseas && overseas >= MAX_OVERSEAS)
            return setError("Overseas player limit reached.");

        if (squad.some(s => s.player_name === selected))
            return setError("Player already purchased.");

        setSquad(prev => [
            ...prev, { ...player, price }
        ]);

        setSelected("");
        setBid("");
    }

    function remove(name) {
        setSquad(prev =>
            prev.filter(p => p.player_name !== name)
        );
        setError("");
    }

    function reset() {
        setSquad([]);
        setSelected("");
        setBid("");
        setError("");
    }

    return (
        <div className="space-y-6">

            <div className="bg-[#111d33] rounded-2xl p-7 border border-pink-500/20">

                <p className="text-pink-400 text-xs tracking-widest">
                    IPL 2027 · STRATEGIC PLANNING
                </p>

                <h2 className="text-3xl font-bold mt-3">
                    Build Your Royal Squad
                </h2>

                <p className="text-slate-400 mt-3">
                    Simulate auction purchases using our
                    pressure-based recruitment recommendations.
                </p>

            </div>

            <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-4">

                {[
                    ["Remaining purse", money(remaining), Wallet],
                    ["Available slots", `${MAX_SLOTS - squad.length}/6`, Users],
                    ["Overseas slots", `${MAX_OVERSEAS - overseas}/3`, Globe],
                    ["Indian purchases", indian, ShoppingCart]
                ].map(([label, value, Icon]) => (
                    <div key={label}
                        className="bg-[#111d33] border border-slate-800 rounded-2xl p-5">

                        <Icon className="text-pink-400 mb-4" />

                        <p className="text-sm text-slate-400">
                            {label}
                        </p>

                        <h2 className="text-3xl font-black mt-2">
                            {value}
                        </h2>

                    </div>
                ))}

            </div>

            <div className="bg-[#111d33] rounded-2xl p-6">

                <div className="flex justify-between mb-4">
                    <h2 className="font-bold">Budget utilisation</h2>
                    <span className="text-pink-400">
                        {money(spent)} / {money(TOTAL_BUDGET)}
                    </span>
                </div>

                <div className="h-4 rounded-full bg-slate-800 overflow-hidden">
                    <div
                        className="bg-pink-500 h-full transition-all"
                        style={{
                            width: `${spent / TOTAL_BUDGET * 100}%`
                        }}
                    />
                </div>

            </div>

            <div className="grid xl:grid-cols-2 gap-6">

                <section className="bg-[#111d33] rounded-2xl p-6">

                    <h2 className="text-xl font-bold mb-6">
                        Auction Room
                    </h2>

                    <input
                        placeholder="Search available players..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                        className="w-full bg-[#080f20] border border-slate-700 rounded-xl p-4 mb-4"
                    />

                    <select
                        value={selected}
                        onChange={e => {
                            setSelected(e.target.value);
                            setError("");
                        }}
                        className="w-full bg-[#080f20] border border-slate-700 rounded-xl p-4"
                    >
                        <option value="">Select a player</option>

                        {available.filter(p =>
                            p.player_name === selected ||
                            p.player_name.toLowerCase()
                                .includes(search.toLowerCase())
                        ).map(p => (
                            <option
                                key={p.player_name}
                                value={p.player_name}
                            >
                                {p.player_name} — {p.nationality}
                            </option>
                        ))}
                    </select>

                    {player && (
                        <div className="bg-[#080f20] rounded-xl p-5 mt-5">

                            <h3 className="text-xl font-bold">
                                {player.player_name}
                            </h3>

                            <p className="text-slate-400 text-sm mt-2">
                                {player.nationality} · {player.role}
                            </p>

                            <div className="grid grid-cols-3 gap-3 mt-5">

                                {[
                                    ["PRI", player.pri],
                                    ["WHI", player.whi],
                                    ["FRS", player.frs]
                                ].map(([label, value]) => (
                                    <div key={label}>
                                        <p className="text-xs text-slate-400">
                                            {label}
                                        </p>
                                        <p className="text-2xl font-bold text-pink-400">
                                            {value == null
                                                ? "N/A"
                                                : Number(value).toFixed(2)}
                                        </p>
                                    </div>
                                ))}

                            </div>

                            <p className="text-sm text-slate-400 mt-5">
                                {player.impact}
                            </p>

                            <p className="text-xs text-amber-400 mt-3">
                                Auction registration unverified
                            </p>

                        </div>
                    )}

                    <label className="block mt-6 text-sm text-slate-400 mb-3">
                        Winning bid (₹ crore)
                    </label>

                    <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        placeholder="Enter bid amount"
                        value={bid}
                        onChange={e => setBid(e.target.value)}
                        className="w-full bg-[#080f20] border border-slate-700 rounded-xl p-4"
                    />

                    {error && (
                        <p className="text-red-400 mt-4 text-sm">
                            {error}
                        </p>
                    )}

                    <button
                        onClick={purchase}
                        className="w-full bg-pink-600 hover:bg-pink-500 rounded-xl py-4 font-bold mt-5"
                    >
                        Purchase Player
                    </button>

                </section>

                <section className="bg-[#111d33] rounded-2xl p-6">

                    <div className="flex justify-between items-center mb-6">

                        <h2 className="text-xl font-bold">
                            Your Auction Picks
                        </h2>

                        <button
                            onClick={reset}
                            className="flex gap-2 items-center text-slate-400 hover:text-pink-400"
                        >
                            <RotateCcw size={16} />
                            Reset
                        </button>

                    </div>

                    {squad.length === 0 && (
                        <p className="text-slate-500 text-center py-16">
                            No players purchased yet.
                        </p>
                    )}

                    <div className="space-y-3">

                        {squad.map(p => (
                            <div
                                key={p.player_name}
                                className="bg-[#080f20] rounded-xl p-4 flex items-center justify-between gap-3"
                            >
                                <div>
                                    <h3 className="font-bold">
                                        {p.player_name}
                                    </h3>

                                    <p className="text-xs text-slate-400 mt-1">
                                        {p.nationality} · {p.role}
                                    </p>
                                </div>

                                <div className="flex gap-4 items-center">

                                    <span className="font-bold text-pink-400">
                                        {money(p.price)}
                                    </span>

                                    <button
                                        onClick={() => remove(p.player_name)}
                                        className="text-slate-400 hover:text-red-400"
                                        aria-label={`Remove ${p.player_name}`}
                                    >
                                        <Trash2 size={18} />
                                    </button>

                                </div>
                            </div>
                        ))}

                    </div>

                    <div className="border-t border-slate-700 mt-6 pt-5">

                        <div className="flex justify-between">
                            <span>Total expenditure</span>
                            <span className="font-bold">{money(spent)}</span>
                        </div>

                        <div className="flex justify-between mt-4">
                            <span>Remaining purse</span>
                            <span className="font-bold text-emerald-400">
                                {money(remaining)}
                            </span>
                        </div>

                    </div>

                </section>

            </div>

            <section className="bg-[#111d33] rounded-2xl p-6">

                <h2 className="text-xl font-bold mb-5">
                    Recruitment Coverage
                </h2>

                <div className="grid md:grid-cols-3 gap-4">

                    {[
                        "Death Bowler",
                        "Middle Order Batter",
                        "Finisher",
                        "Powerplay Bowler",
                        "Middle Over Bowler",
                        "Backup Opener"
                    ].map(role => {

                        const count = squad.filter(
                            p => p.role === role
                        ).length;

                        return (
                            <div key={role}
                                className="bg-[#080f20] rounded-xl p-5">

                                <p className="text-sm text-slate-400">
                                    {role}
                                </p>

                                <h3 className={`font-bold mt-3 ${count > 0
                                    ? "text-emerald-400"
                                    : "text-slate-500"
                                    }`}>
                                    {count > 0
                                        ? `${count} recruited`
                                        : "Not selected"}
                                </h3>

                            </div>
                        );
                    })}

                </div>
            </section>

            <p className="text-xs text-slate-500">
                Hypothetical auction simulation. Purse and slot
                constraints are provisional inputs. Bid amounts
                are user-defined, not predicted auction prices.
                Player eligibility and registration require verification.
            </p>

        </div>
    );
}
