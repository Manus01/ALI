import React, { useState } from 'react';
import useIntegrations from '../hooks/useIntegrations';
import IntegrationModal from '../components/IntegrationModal';

const PLATFORMS = [
  { id: 'google_ads', name: 'Google Ads' },
  { id: 'google_analytics', name: 'Google Analytics' },
  { id: 'facebook_ads', name: 'Facebook Ads' },
  { id: 'linkedin_ads', name: 'LinkedIn Ads' },
  { id: 'openai', name: 'OpenAI' },
  { id: 'gemini', name: 'Gemini AI' }
];

export default function Integrations() {
  const { integrations, loading, saveApiKey } = useIntegrations();
  const [active, setActive] = useState(null);

  const openModal = (platform) => setActive(platform);
  const closeModal = () => setActive(null);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Integrations</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PLATFORMS.map(p => {
          const keyField = p.id + '_key';
          const status = integrations && integrations[keyField] ? 'Connected' : 'Disconnected';
          return (
            <div key={p.id} className="p-4 bg-gray-50 dark:bg-gray-900 rounded shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{p.name}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300">Status: <strong>{status}</strong></p>
                </div>
                <div>
                  <button onClick={() => openModal(p)} className="px-3 py-1 bg-indigo-600 text-white rounded">Manage</button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {active && (
        <IntegrationModal
          platform={active}
          defaultKey={(integrations && integrations[active.id + '_key']) || ''}
          onClose={closeModal}
          onSave={async (key) => {
            const res = await saveApiKey(active.id, key);
            return res;
          }}
        />
      )}
    </div>
  );
}
