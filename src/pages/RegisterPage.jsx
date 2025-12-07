import React, { useState } from 'react';
import { createUserWithEmailAndPassword } from 'firebase/auth';
import { doc, setDoc } from 'firebase/firestore';
import { auth, db } from '../firebase';
import { useNavigate } from 'react-router-dom';

export default function RegisterPage() {
  const [form, setForm] = useState({
    email: '',
    password: '',
    name: '',
    surname: '',
    age: '',
    sex: '',
    job: '',
    industry: '',
    education: '',
    companySize: '',
    website: ''
  });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const userCred = await createUserWithEmailAndPassword(auth, form.email, form.password);
      const uid = userCred.user.uid;
      // Save profile in Firestore
      await setDoc(doc(db, 'users', uid), {
        name: form.name,
        surname: form.surname,
        age: form.age,
        sex: form.sex,
        job: form.job,
        industry: form.industry,
        education: form.education,
        companySize: form.companySize || null,
        website: form.website || null,
        quizzesCompleted: {
          hiddenFigures: false,
          marketing: false,
          eq: false
        },
        createdAt: new Date().toISOString()
      });
      // Redirect to first quiz (example path)
      navigate('/quiz/hidden-figures');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="max-w-md mx-auto p-4">
      <h2 className="text-2xl font-bold mb-4">Create account</h2>
      {error && <div className="mb-3 text-red-600">{error}</div>}
      <form onSubmit={onSubmit} className="space-y-2">
        <input name="email" value={form.email} onChange={onChange} placeholder="Email" className="w-full p-2 border rounded" />
        <input name="password" value={form.password} onChange={onChange} placeholder="Password" type="password" className="w-full p-2 border rounded" />
        <input name="name" value={form.name} onChange={onChange} placeholder="Name" className="w-full p-2 border rounded" />
        <input name="surname" value={form.surname} onChange={onChange} placeholder="Surname" className="w-full p-2 border rounded" />
        <input name="age" value={form.age} onChange={onChange} placeholder="Age" className="w-full p-2 border rounded" />
        <input name="sex" value={form.sex} onChange={onChange} placeholder="Sex" className="w-full p-2 border rounded" />
        <input name="job" value={form.job} onChange={onChange} placeholder="Job" className="w-full p-2 border rounded" />
        <input name="industry" value={form.industry} onChange={onChange} placeholder="Industry" className="w-full p-2 border rounded" />
        <input name="education" value={form.education} onChange={onChange} placeholder="Education Level" className="w-full p-2 border rounded" />
        <input name="companySize" value={form.companySize} onChange={onChange} placeholder="Company Size (optional)" className="w-full p-2 border rounded" />
        <input name="website" value={form.website} onChange={onChange} placeholder="Website URL (optional)" className="w-full p-2 border rounded" />
        <button type="submit" className="px-4 py-2 bg-indigo-600 text-white rounded">Register</button>
      </form>
    </div>
  );
}
