import React, { useState } from 'react';

export default function SuggestionsModal({ suggestions = [], onClose, onEvaluate }) {
  const [feedbackState, setFeedbackState] = useState({});

  const handleFeedback = async (id, feedback) => {
    setFeedbackState((s) => ({ ...s, [id]: 'saving' }));
    await onEvaluate(id, feedback);
    setFeedbackState((s) => ({ ...s, [id]: feedback }));
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded shadow-lg w-full max-w-2xl p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">AI Suggestions</h3>
          <button onClick={onClose} className="text-sm">Close</button>
        </div>

        <div className="space-y-4">
          {suggestions.map(s => (
            <div key={s.id} className="p-3 bg-gray-50 dark:bg-gray-800 rounded">
              <div className="font-semibold mb-1">{s.title}</div>
              <div className="text-sm mb-2">{s.rationale}</div>
              <div className="flex items-center space-x-2">
                <button onClick={() => handleFeedback(s.id, 'Worked Well')} className="px-3 py-1 bg-green-600 text-white rounded">Worked Well</button>
                <button onClick={() => handleFeedback(s.id, 'Did Not Work')} className="px-3 py-1 bg-red-600 text-white rounded">Did Not Work</button>
                <div className="text-sm">{feedbackState[s.id]}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
