import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword } from "firebase/auth";
import { doc, setDoc } from "firebase/firestore";
import { auth, db } from "../firebase";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [companySize, setCompanySize] = useState("1-10");
  const [industry, setIndustry] = useState("E-commerce");
  const [role, setRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (!fullName.trim() || !email.trim() || !password.trim() || !role.trim()) {
      setError("Please complete all required fields.");
      return;
    }

    setLoading(true);
    try {
      const userCredential = await createUserWithEmailAndPassword(auth, email, password);
      const user = userCredential.user;

      const userData = {
        email: user.email,
        name: fullName,
        profile: {
          company_size: companySize,
          industry,
          role,
        },
        onboarding_status: "pending",
        created_at: new Date().toISOString(),
      };

      await setDoc(doc(db, "users", user.uid), userData);

      navigate("/quiz/hft");
    } catch (err) {
      console.error("Registration error:", err);
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left - Branding */}
      <div className="hidden lg:flex w-1/2 bg-gradient-to-br from-blue-700 to-indigo-600 items-center justify-center p-12">
        <div className="max-w-md text-white">
          <div className="mb-6">
            <h1 className="text-4xl font-extrabold">ALI Platform</h1>
            <p className="mt-4 text-lg opacity-90">AI-driven insights to accelerate your product decisions and growth.</p>
          </div>

          <div className="glass-panel p-6 rounded-xl shadow-lg bg-white/5">
            <h2 className="text-2xl font-semibold mb-2">Hidden Figures Test</h2>
            <p className="text-sm opacity-90">Quick diagnostic to personalize your onboarding and give targeted recommendations.</p>
          </div>

          <div className="mt-8 text-sm opacity-90">
            <p>Trusted by teams building the future of commerce and SaaS.</p>
          </div>
        </div>
      </div>

      {/* Right - Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-lg">
          <div className="glass-panel p-8 rounded-2xl shadow-md">
            <h2 className="text-2xl font-bold mb-1">Create your account</h2>
            <p className="text-sm text-gray-500 mb-6">Start your free trial and take the Hidden Figures Test to get tailored insights.</p>

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">{error}</div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Name &amp; Surname</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-200 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Jane Doe"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-200 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="you@company.com"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Password</label>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-200 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="Choose a strong password"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Company Size</label>
                  <select
                    value={companySize}
                    onChange={(e) => setCompanySize(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-200 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="1-10">1-10</option>
                    <option value="11-50">11-50</option>
                    <option value="50+">50+</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">Industry</label>
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-200 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="E-commerce">E-commerce</option>
                    <option value="SaaS">SaaS</option>
                    <option value="Agency">Agency</option>
                    <option value="Other">Other</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Role</label>
                <input
                  type="text"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="mt-1 block w-full rounded-md border-gray-200 shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="e.g. Head of Product"
                  required
                />
              </div>

              <div className="pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full inline-flex items-center justify-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-60"
                >
                  {loading ? "Creating account..." : "Create account"}
                </button>
              </div>

              <p className="text-xs text-gray-500 mt-3">By creating an account you agree to our Terms and Privacy Policy.</p>
            </form>
          </div>

          <div className="mt-4 text-center text-sm text-gray-500">
            Already have an account? <a href="/login" className="text-indigo-600 font-medium">Sign in</a>
          </div>
        </div>
      </div>
    </div>
  );
}
