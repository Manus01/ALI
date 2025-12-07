import React, { useState, useEffect } from 'react';

const PLATFORM_FIELDS = {
  facebook: [{ name: 'apiKey', label: 'API Key' }],
  instagram: [{ name: 'apiKey', label: 'API Key' }],
  openai: [{ name: 'apiKey', label: 'API Key' }],
  linkedin: [{ name: 'clientId', label: 'Client ID' }, { name: 'clientSecret', label: 'Client Secret' }],
  google_analytics: [{ name: 'apiKey', label: 'API Key' }],
  google_adwords: [{ name: 'apiKey', label: 'API Key' }],
  facebook_ads: [{ name: 'accessToken', label: 'Access Token' }],
  yandex_ads: [{ name: 'token', label: 'Token' }],
  bing_ads: [{ name: 'apiKey', label: 'API Key' }]
};

export default function IntegrationModal({ platform, defaultCredentials = {}, onClose, onSave }) {
  const [credentials, setCredentials] = useState(defaultCredentials || {});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [validation, setValidation] = useState(null);

  useEffect(() => {
    setCredentials(defaultCredentials || {});
    setValidation(null);
    setMessage('');
  }, [defaultCredentials, platform]);

  const fields = PLATFORM_FIELDS[platform.id] || [{ name: 'apiKey', label: 'API Key' }];

  const runValidation = async (creds) => {
    // lightweight client-side heuristics
    if (Object.values(creds).every(v => !v)) {
      setValidation({ ok: false, message: 'Please enter credentials' });
      return false;
    }
    setValidation({ ok: true, message: 'Looks good — will validate on save' });
    return true;
  };

  const handleChange = (name, value) => {
    const next = { ...credentials, [name]: value };
    setCredentials(next);
    runValidation(next);
  };

  const handleSave = async () => {
    setLoading(true);
    setMessage('');
    try {
      const ok = await runValidation(credentials);
      if (!ok) {
        setMessage('Fix validation errors');
        setLoading(false);
        return;
      }
      const res = await onSave(credentials);
      if (res && res.success) {
        setMessage('Saved and connected');
      } else {
        const msg = (res && res.validation && res.validation.statusMessage) || res.message || 'Failed to save';
        setMessage(msg);
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
          <p className="text-sm text-gray-700 dark:text-gray-300">Follow the instructions and enter the required credentials below.</p>
        </div>

        <div className="space-y-3 mb-4">
          {fields.map(f => (
            <div key={f.name}>
              <label className="block text-sm mb-1">{f.label}</label>
              <input value={credentials[f.name] || ''} onChange={(e) => handleChange(f.name, e.target.value)} className="w-full p-2 border rounded bg-white dark:bg-gray-800" />
            </div>
          ))}
        </div>

        {validation && <div className={`mb-3 text-sm ${validation.ok ? 'text-green-600' : 'text-red-600'}`}>{validation.message}</div>}
        {message && <div className="mb-3 text-sm">{message}</div>}

        <div className="flex justify-end space-x-2">
          <button onClick={onClose} className="px-3 py-1 border rounded">Cancel</button>
          <button onClick={handleSave} disabled={loading} className="px-3 py-1 bg-indigo-600 text-white rounded">{loading ? 'Saving...' : 'Save'}</button>
        </div>
      </div>
    </div>
  );
}
