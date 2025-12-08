import React, { useState } from 'react';
import useIntegrations from '../hooks/useIntegrations';
import { PLATFORMS } from '../hooks/useIntegrations';
import IntegrationModal from '../components/IntegrationModal';

export default function Integrations() {
  const { integrations, loading, saveCredentials } = useIntegrations();
  const [active, setActive] = useState(null);

  const openModal = (platform) => setActive(platform);
  const closeModal = () => setActive(null);

  const palette = {
    facebook: 'from-blue-500 to-blue-700',
    instagram: 'from-pink-500 to-orange-500',
    linkedin: 'from-sky-500 to-blue-700',
    google_ads: 'from-amber-500 to-orange-600',
    google_analytics: 'from-emerald-500 to-lime-500',
    yandex_ads: 'from-red-500 to-rose-600',
    bing_ads: 'from-indigo-500 to-purple-600',
    tiktok: 'from-cyan-500 to-slate-900',
    x: 'from-slate-500 to-gray-800'
  };

  const statusBadge = (status) => {
    if (status === 'OK') return 'bg-emerald-500/15 text-emerald-100 border-emerald-500/30';
    if (!status || status === 'Disconnected') return 'bg-slate-500/10 text-slate-200 border-slate-500/20';
    return 'bg-amber-500/15 text-amber-100 border-amber-500/30';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-white/60">Connections</p>
          <h2 className="text-3xl font-bold text-white">Integrations</h2>
          <p className="text-slate-200">Manage every platform from a responsive, card-based hub.</p>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {PLATFORMS.map(p => {
          const status = integrations && integrations[`${p.id}_status`] ? integrations[`${p.id}_status`] : 'Disconnected';
          const statusMessage = integrations && integrations[`${p.id}_statusMessage`];
          const lastSync = integrations && integrations[`${p.id}_lastSyncTime`];
          return (
            <div
              key={p.id}
              className="rounded-2xl bg-white/5 border border-white/10 shadow-xl hover:border-white/20 transition flex flex-col h-full"
            >
              <div className="p-5 flex items-start gap-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${palette[p.id] || 'from-indigo-500 to-purple-600'} flex items-center justify-center text-white font-semibold shadow-lg shadow-black/20`}>{p.name[0]}</div>
                <div className="flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-white">{p.name}</h3>
                    <span className={`text-xs px-3 py-1 rounded-full border ${statusBadge(status)}`}>{status}</span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1">{p.description || 'Keep this connection healthy to power insights.'}</p>
                </div>
              </div>
              <div className="px-5 pb-5 mt-auto space-y-2 text-sm text-slate-200">
                {statusMessage && <p className="text-amber-200">{statusMessage}</p>}
                {lastSync && <p className="text-xs text-slate-400">Last sync: {new Date(lastSync.toMillis ? lastSync.toMillis() : lastSync).toLocaleString()}</p>}
                <div className="flex justify-end">
                  <button onClick={() => openModal(p)} className="px-4 py-2 rounded-lg bg-gradient-to-r from-indigo-500 to-cyan-500 text-white font-semibold shadow-md hover:shadow-lg transition">Manage</button>
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
