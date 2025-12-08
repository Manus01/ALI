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
  const [fieldErrors, setFieldErrors] = useState({});
  const navigate = useNavigate();

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const validate = () => {
    const errs = {};
    if (!form.email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) errs.email = 'Enter a valid email';
    if (!form.password || form.password.length < 6) errs.password = 'Password must be at least 6 characters';
    if (!form.name) errs.name = 'First name required';
    if (!form.surname) errs.surname = 'Surname required';
    if (!form.age || isNaN(Number(form.age)) || Number(form.age) <= 0) errs.age = 'Enter a valid age';
    if (!form.job) errs.job = 'Job is required';
    if (!form.industry) errs.industry = 'Industry is required';
    if (!form.education) errs.education = 'Education level is required';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!validate()) return;
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
      // Redirect to first quiz
      navigate('/quiz/hft');
    } catch (err) {
      setError(err.message);
    }
  };

  const inputClass = (name) => `w-full p-3 border rounded focus:outline-none focus:ring-2 focus:ring-indigo-300 placeholder-gray-400 ${fieldErrors[name] ? 'border-red-500' : 'border-gray-200 dark:border-gray-700'}`;

  return (
    <div className="max-w-md mx-auto p-6">
      <h2 className="text-2xl font-bold mb-4">Create account</h2>
      {error && <div className="mb-3 text-red-600">{error}</div>}
      <form onSubmit={onSubmit} className="space-y-3">
        <div>
          <label className="text-sm">Email</label>
          <input name="email" value={form.email} onChange={onChange} placeholder="you@example.com" className={inputClass('email')} />
          {fieldErrors.email && <div className="text-xs text-red-500 mt-1">{fieldErrors.email}</div>}
        </div>

        <div>
          <label className="text-sm">Password</label>
          <input name="password" value={form.password} onChange={onChange} placeholder="At least 6 characters" type="password" className={inputClass('password')} />
          {fieldErrors.password && <div className="text-xs text-red-500 mt-1">{fieldErrors.password}</div>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm">First name</label>
            <input name="name" value={form.name} onChange={onChange} placeholder="First name" className={inputClass('name')} />
            {fieldErrors.name && <div className="text-xs text-red-500 mt-1">{fieldErrors.name}</div>}
          </div>
          <div>
            <label className="text-sm">Surname</label>
            <input name="surname" value={form.surname} onChange={onChange} placeholder="Surname" className={inputClass('surname')} />
            {fieldErrors.surname && <div className="text-xs text-red-500 mt-1">{fieldErrors.surname}</div>}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="text-sm">Age</label>
            <input name="age" value={form.age} onChange={onChange} placeholder="Age" className={inputClass('age')} />
            {fieldErrors.age && <div className="text-xs text-red-500 mt-1">{fieldErrors.age}</div>}
          </div>
          <div>
            <label className="text-sm">Sex</label>
            <input name="sex" value={form.sex} onChange={onChange} placeholder="M / F / Other" className={inputClass('sex')} />
          </div>
          <div>
            <label className="text-sm">Job</label>
            <input name="job" value={form.job} onChange={onChange} placeholder="Your role" className={inputClass('job')} />
            {fieldErrors.job && <div className="text-xs text-red-500 mt-1">{fieldErrors.job}</div>}
          </div>
        </div>

        <div>
          <label className="text-sm">Industry</label>
          <input name="industry" value={form.industry} onChange={onChange} placeholder="Industry" className={inputClass('industry')} />
          {fieldErrors.industry && <div className="text-xs text-red-500 mt-1">{fieldErrors.industry}</div>}
        </div>

        <div>
          <label className="text-sm">Education level</label>
          <input name="education" value={form.education} onChange={onChange} placeholder="e.g., Bachelor's, Master's" className={inputClass('education')} />
          {fieldErrors.education && <div className="text-xs text-red-500 mt-1">{fieldErrors.education}</div>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <input name="companySize" value={form.companySize} onChange={onChange} placeholder="Company size (optional)" className="w-full p-3 border rounded focus:outline-none focus:ring-2 focus:ring-indigo-300" />
          <input name="website" value={form.website} onChange={onChange} placeholder="Website URL (optional)" className="w-full p-3 border rounded focus:outline-none focus:ring-2 focus:ring-indigo-300" />
        </div>

        <div>
          <button type="submit" className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded font-medium">Create account</button>
        </div>
      </form>
    </div>
  );
}
