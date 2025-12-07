import React from 'react';
import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Welcome back</h2>

      <section className="grid gap-4 md:grid-cols-3 mb-6">
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow-sm">
          <h3 className="font-semibold">Quick Start</h3>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Jump in with a new tutorial or explore integrations.</p>
          <Link to="/tutorials" className="inline-block mt-3 text-indigo-600 dark:text-indigo-400">Browse tutorials →</Link>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow-sm">
          <h3 className="font-semibold">Integrations</h3>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Connect external services to enhance functionality.</p>
          <Link to="/integrations" className="inline-block mt-3 text-indigo-600 dark:text-indigo-400">Manage integrations →</Link>
        </div>
        <div className="p-4 bg-white dark:bg-gray-800 rounded shadow-sm">
          <h3 className="font-semibold">Account</h3>
          <p className="text-sm text-gray-600 dark:text-gray-300 mt-2">Sign in to access personalized features.</p>
          <Link to="/login" className="inline-block mt-3 text-indigo-600 dark:text-indigo-400">Sign in →</Link>
        </div>
      </section>

      <section>
        <h3 className="text-xl font-semibold mb-2">Recent activity</h3>
        <div className="space-y-2 text-gray-700 dark:text-gray-300">
          <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded">You viewed "Getting started" tutorial</div>
          <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded">Integration with ExampleService configured</div>
        </div>
      </section>
    </div>
  );
}
