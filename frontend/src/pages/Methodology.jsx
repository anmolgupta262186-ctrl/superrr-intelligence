
export default function Methodology() {

    const models = [
        {
            name: "PRI",
            full: "Pressure Reliability Index",
            desc: "Measures player reliability under high pressure relative to baseline performance.",
            metrics: [
                "Performance improvement",
                "Dismissal or wicket-taking improvement",
                "Absolute pressure performance",
                "Consistency",
                "Sample reliability",
            ],
        },
        {
            name: "WHI",
            full: "Weakness Handling Index",
            desc: "Measures performance against the specific cricketing weaknesses identified in Rajasthan Royals.",
            metrics: [
                "Run control",
                "Wicket-taking ability",
                "Strike rate",
                "Boundary scoring",
                "Dot-ball performance",
            ],
        },
        {
            name: "RRI",
            full: "Recruitment Reliability Index",
            desc: "Combines pressure reliability and weakness handling.",
            formula: "RRI = 0.5 × PRI + 0.5 × WHI",
        },
        {
            name: "FRS",
            full: "Final Recruitment Score",
            desc: "Combines analytical performance with Rajasthan Royals' squad priorities.",
            formula: "FRS = 0.4 × PRI + 0.4 × WHI + 0.2 × Squad Priority",
        },
    ];

    return (
        <div className="space-y-6">

            {models.map(model => (
                <div key={model.name}
                    className="bg-[#111d33] rounded-2xl p-7 border border-slate-800">

                    <span className="text-pink-400 text-3xl font-black">
                        {model.name}
                    </span>

                    <h2 className="text-xl font-bold mt-2">
                        {model.full}
                    </h2>

                    <p className="text-slate-400 mt-3">
                        {model.desc}
                    </p>

                    {model.formula && (
                        <div className="bg-[#080f20] rounded-xl p-5 mt-5 text-pink-400 font-mono">
                            {model.formula}
                        </div>
                    )}

                    {model.metrics && (
                        <div className="flex flex-wrap gap-3 mt-5">
                            {model.metrics.map(m => (
                                <span key={m}
                                    className="bg-slate-800 rounded-lg px-4 py-2 text-sm">
                                    {m}
                                </span>
                            ))}
                        </div>
                    )}
                </div>
            ))}

            <div className="bg-[#111d33] rounded-2xl p-7">
                <h2 className="text-xl font-bold mb-4">
                    Data Limitations
                </h2>

                {[
                    "Different competition levels are not fully calibrated.",
                    "Normal and Moderate pressure baselines are evaluated separately.",
                    "Historical SMAT performances do not establish current form.",
                    "Auction registration and player availability require verification.",
                    "State-level leagues have incomplete data coverage.",
                    "Official bowling run rate excludes extras.",
                    "Pressure-definition sensitivity requires further validation.",
                ].map(item => (
                    <p key={item} className="text-slate-400 py-3 border-b border-slate-800">
                        {item}
                    </p>
                ))}
            </div>

        </div>
    );
}
