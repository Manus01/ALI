import React, { useState } from 'react';
import useIntegrations from '../hooks/useIntegrations';
import { PLATFORMS } from '../hooks/useIntegrations';
import IntegrationModal from '../components/IntegrationModal';

export default function Integrations() {
  const { integrations, loading, saveCredentials } = useIntegrations();
  const [active, setActive] = useState(null);

  const openModal = (platform) => setActive(platform);
  const closeModal = () => setActive(null);

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Integrations</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {PLATFORMS.map(p => {
          const status = integrations && integrations[`${p.id}_status`] ? integrations[`${p.id}_status`] : 'Disconnected';
          const statusMessage = integrations && integrations[`${p.id}_statusMessage`];
          const lastSync = integrations && integrations[`${p.id}_lastSyncTime`];
          return (
            <div key={p.id} className="p-4 bg-gray-50 dark:bg-gray-900 rounded shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{p.name}</h3>
                  <p className="text-sm text-gray-600 dark:text-gray-300">Status: <strong>{status}</strong></p>
                  {statusMessage && <p className="text-xs text-red-500">{statusMessage}</p>}
                  {lastSync && <p className="text-xs text-gray-500">Last sync: {new Date(lastSync.toMillis ? lastSync.toMillis() : lastSync).toLocaleString()}</p>}
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
          defaultCredentials={{}}
          onClose={closeModal}
          onSave={async (creds) => {
            const res = await saveCredentials(active.id, creds);
            return res;
          }}
        />
      )}
    </div>
  );
}
