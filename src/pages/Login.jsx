import React from 'react';
import { Link } from 'react-router-dom';

export default function Login() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Sign in</h2>
      <form className="space-y-3 max-w-sm">
        <input className="w-full p-2 border rounded" placeholder="Email" />
        <input className="w-full p-2 border rounded" placeholder="Password" type="password" />
        <button className="px-3 py-2 bg-indigo-600 text-white rounded">Sign in</button>
      </form>
      <p className="mt-4 text-sm">Don't have an account? <Link to="/register" className="text-indigo-600">Register</Link></p>
    </div>
  );
}
