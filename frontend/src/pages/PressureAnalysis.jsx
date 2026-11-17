
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from "recharts";

export default function PressureAnalysis() {

    const data = [
        { condition: "Normal", Batting: 104022, Bowling: 115089 },
        { condition: "Moderate", Batting: 43619, Bowling: 54912 },
        { condition: "High", Batting: 46373, Bowling: 21795 },
        { condition: "Uncertain", Batting: 6947, Bowling: 9165 },
    ];

    const battingConditions = [
        "Four or more wickets lost",
        "Six or more wickets lost",
        "Required run rate of 10 or above",
        "Required run rate exceeds current run rate by 2 or more after 30 balls",
        "Close chase during the final 30 balls",
        "Knockout match",
    ];

    const bowlingConditions = [
        "Opposition scoring at 10 or more after 12 balls",
        "Wicketless powerplay after 24 balls",
        "Two or fewer wickets taken after 60 balls in the middle phase",
        "Opposition requires 8 or fewer runs per over with at least five wickets remaining",
        "Established batting side during death overs",
        "Close chase",
        "Knockout match",
    ];

    return (
        <div className="space-y-6">

            <div className="grid md:grid-cols-3 gap-5">
                {[
                    ["Normal", "0 pressure points", "text-blue-400"],
                    ["Moderate", "1 pressure point", "text-yellow-400"],
                    ["High", "2 or more pressure points", "text-pink-400"],
                ].map(([name, value, color]) => (
                    <div key={name} className="bg-[#111d33] p-6 rounded-2xl border border-slate-800">
                        <h2 className={`text-2xl font-bold ${color}`}>
                            {name}
                        </h2>
                        <p className="text-slate-400 mt-3">{value}</p>
                    </div>
                ))}
            </div>

            <div className="bg-[#111d33] rounded-2xl p-6">
                <h2 className="text-xl font-bold mb-2">
                    Pressure Distribution
                </h2>
                <p className="text-slate-400 text-sm mb-6">
                    Official RR dataset — delivery-level classification
                </p>

                <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={data}>
                        <CartesianGrid stroke="#29364d" strokeDasharray="3 3" />
                        <XAxis dataKey="condition" tick={{ fill: "#94a3b8" }} />
                        <YAxis tick={{ fill: "#94a3b8" }} />
                        <Tooltip contentStyle={{ background: "#172544", border: "none" }} />
                        <Legend />
                        <Bar dataKey="Batting" fill="#ea1a85" radius={[6, 6, 0, 0]} />
                        <Bar dataKey="Bowling" fill="#648be0" radius={[6, 6, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </div>

            <div className="grid xl:grid-cols-2 gap-6">
                {[
                    ["Batting Pressure Conditions", battingConditions],
                    ["Bowling Pressure Conditions", bowlingConditions],
                ].map(([title, conditions]) => (
                    <div key={title} className="bg-[#111d33] rounded-2xl p-6">
                        <h2 className="text-xl font-bold mb-5">{title}</h2>

                        {conditions.map((condition, i) => (
                            <div key={i} className="flex gap-4 p-4 border-b border-slate-800">
                                <span className="text-pink-400 font-bold">
                                    0{i + 1}
                                </span>
                                <p className="text-slate-300">{condition}</p>
                            </div>
                        ))}
                    </div>
                ))}
            </div>

            <div className="bg-[#111d33] rounded-2xl p-6">
                <h2 className="text-xl font-bold mb-5">
                    Match Phase Classification
                </h2>

                <div className="flex h-14 rounded-xl overflow-hidden text-sm font-bold">
                    <div className="w-[30%] bg-blue-600 flex items-center justify-center">
                        Powerplay
                    </div>
                    <div className="w-[45%] bg-purple-600 flex items-center justify-center">
                        Middle
                    </div>
                    <div className="w-[25%] bg-pink-600 flex items-center justify-center">
                        Death
                    </div>
                </div>

                <div className="flex justify-between text-slate-400 mt-3">
                    <span>Over 1</span>
                    <span>Over 6</span>
                    <span>Over 15</span>
                    <span>Over 20</span>
                </div>
            </div>

            <p className="text-sm text-slate-400">
                Uncertain deliveries are excluded from pressure comparisons.
                Official match-state scores are estimated where extras are ambiguous.
                Pressure signals are rule-based, not calibrated probabilities.
            </p>
        </div>
    );
}
