import React from 'react';

export default function Integrations() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Integrations</h2>
      <p className="text-gray-700 dark:text-gray-300 mb-4">Manage integrations that connect external services.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded">ExampleService — Connected</div>
        <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded">AnotherService — Not connected</div>
      </div>
    </div>
  );
}
