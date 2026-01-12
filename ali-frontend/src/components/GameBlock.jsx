import React, { useState } from 'react';

export default function GameBlock({ block }) {
    const [result, setResult] = useState(null);

    if (!block) return null;

    const { game_type: gameType, title, instructions, config } = block;

    if (gameType === 'fixer') {
        return (
            <div className="mb-8 rounded-xl border border-amber-200 bg-amber-50 p-6">
                <h4 className="text-sm font-bold text-amber-800 mb-2">{title || "Fix It"}</h4>
                <p className="text-sm text-amber-700 mb-4">{instructions || config?.prompt}</p>
                <div className="space-y-2">
                    {(config?.options || []).map((opt, idx) => (
                        <button
                            key={idx}
                            onClick={() => setResult(idx === config?.correctIndex)}
                            className="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-left text-sm hover:bg-amber-100"
                        >
                            {opt}
                        </button>
                    ))}
                </div>
                {result !== null && (
                    <p className={`mt-3 text-xs font-bold ${result ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {result ? "Correct ✅" : "Try again 🔁"}
                    </p>
                )}
            </div>
        );
    }

    if (gameType === 'scenario') {
        return (
            <div className="mb-8 rounded-xl border border-indigo-200 bg-indigo-50 p-6">
                <h4 className="text-sm font-bold text-indigo-800 mb-2">{title || "Scenario"}</h4>
                <p className="text-sm text-indigo-700 mb-4">{instructions || config?.prompt}</p>
                <div className="space-y-2">
                    {(config?.choices || []).map((choice) => (
                        <button
                            key={choice.value}
                            onClick={() => setResult(choice.value === config?.correctValue)}
                            className="w-full rounded-lg border border-indigo-200 bg-white px-3 py-2 text-left text-sm hover:bg-indigo-100"
                        >
                            {choice.label}
                        </button>
                    ))}
                </div>
                {result !== null && (
                    <p className={`mt-3 text-xs font-bold ${result ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {result ? "Correct ✅" : "Not quite. Review the section and try again."}
                    </p>
                )}
            </div>
        );
    }

    const [leftItems, rightItems] = (config?.items || []).reduce(
        (acc, item) => {
            acc[item.category === 'right' ? 1 : 0].push(item);
            return acc;
        },
        [[], []]
    );

    return (
        <div className="mb-8 rounded-xl border border-slate-200 bg-white p-6">
            <h4 className="text-sm font-bold text-slate-800 mb-2">{title || "Sorter"}</h4>
            <p className="text-sm text-slate-600 mb-4">{instructions}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                    <p className="text-xs font-bold text-slate-500 mb-2">{config?.leftLabel || "Left"}</p>
                    <ul className="space-y-2">
                        {leftItems.map((item) => (
                            <li key={item.label} className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-700">
                                {item.label}
                            </li>
                        ))}
                    </ul>
                </div>
                <div>
                    <p className="text-xs font-bold text-slate-500 mb-2">{config?.rightLabel || "Right"}</p>
                    <ul className="space-y-2">
                        {rightItems.map((item) => (
                            <li key={item.label} className="rounded-lg bg-rose-50 px-3 py-2 text-rose-700">
                                {item.label}
                            </li>
                        ))}
                    </ul>
                </div>
            </div>
            <p className="mt-3 text-xs text-slate-400">Tap an item to discuss why it belongs in each group.</p>
        </div>
    );
}
