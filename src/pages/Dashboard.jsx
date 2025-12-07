import React from 'react';
import useIntegrations from '../hooks/useIntegrations';
import { Link } from 'react-router-dom';

export default function Dashboard(){
  const { integrations, PLATFORMS } = useIntegrations();

  const problematic = PLATFORMS.filter(p => {
    const status = integrations && integrations[`${p.id}_status`];
    return status && status !== 'OK';
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Dashboard</h2>
      <section className="mb-6">
        <h3 className="font-semibold mb-2">Integrations health</h3>
        {problematic.length === 0 ? (
          <p className="text-sm text-gray-600 dark:text-gray-300">All integrations healthy.</p>
        ) : (
          <div className="space-y-2">
            {problematic.map(p => (
              <div key={p.id} className="p-3 bg-yellow-50 dark:bg-yellow-900 rounded">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-semibold">{p.name}</div>
                    <div className="text-sm text-gray-700 dark:text-gray-300">{(integrations && integrations[`${p.id}_statusMessage`]) || 'Needs attention'}</div>
                  </div>
                  <div>
                    <Link to="/integrations" className="text-indigo-600">Manage</Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
