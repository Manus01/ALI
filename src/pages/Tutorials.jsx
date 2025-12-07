import React from 'react';
import { Link } from 'react-router-dom';

const tutorials = [
  { id: 'getting-started', title: 'Getting started' },
  { id: 'advanced-workflows', title: 'Advanced workflows' }
];

export default function Tutorials() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Tutorials</h2>
      <ul className="space-y-3">
        {tutorials.map(t => (
          <li key={t.id} className="p-3 bg-gray-50 dark:bg-gray-900 rounded">
            <Link to={`#/tutorials/${t.id}`} className="text-indigo-600 dark:text-indigo-400">{t.title}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
