import React from 'react';

export default function Register() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Create account</h2>
      <form className="space-y-3 max-w-sm">
        <input className="w-full p-2 border rounded" placeholder="Email" />
        <input className="w-full p-2 border rounded" placeholder="Password" type="password" />
        <button className="px-3 py-2 bg-indigo-600 text-white rounded">Create account</button>
      </form>
    </div>
  );
}
