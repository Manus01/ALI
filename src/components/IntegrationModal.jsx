import React, { useState } from 'react';

export default function IntegrationModal({ platform, defaultKey = '', onClose, onSave }) {
  const [key, setKey] = useState(defaultKey);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const instructions = {
    google_ads: 'Go to Google Ads > API > Create/Copy your API key in the developer console.',
    google_analytics: 'Go to Google Analytics > Admin > Data Streams > Measurement Protocol to get credentials.',
    facebook_ads: 'Go to Facebook Business > Integrations > Generate access token.',
    linkedin_ads: 'Go to LinkedIn Developer > Create App > Auth to get Client ID/Secret.',
    openai: 'Visit OpenAI dashboard > API keys to create a new key.',
    gemini: 'Go to Google AI Studio > API Key Management to generate your key.'
  };

  const handleSave = async () => {
    setLoading(true);
    setMessage('');
    try {
      const res = await onSave(key);
      if (res && res.success) {
        setMessage('Saved successfully');
      } else {
        setMessage(res.message || 'Failed to save');
      }
    } catch (e) {
      setMessage(e.message || 'Error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-900 rounded shadow-lg w-full max-w-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Configure {platform.name}</h3>
          <button onClick={onClose} className="text-sm">Close</button>
        </div>

        <div className="mb-4">
          <p className="text-sm text-gray-700 dark:text-gray-300">{instructions[platform.id]}</p>
        </div>

        <div className="mb-4">
          <label className="block text-sm mb-1">API Key</label>
          <input value={key} onChange={(e) => setKey(e.target.value)} className="w-full p-2 border rounded bg-white dark:bg-gray-800" />
        </div>

        {message && <div className="mb-3 text-sm">{message}</div>}

        <div className="flex justify-end space-x-2">
          <button onClick={onClose} className="px-3 py-1 border rounded">Cancel</button>
          <button onClick={handleSave} disabled={loading} className="px-3 py-1 bg-indigo-600 text-white rounded">{loading ? 'Saving...' : 'Save'}</button>
        </div>
      </div>
    </div>
  );
}
