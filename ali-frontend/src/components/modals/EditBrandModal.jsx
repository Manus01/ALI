import React, { useState, useEffect } from 'react';
import { FaTimes, FaCloudUploadAlt, FaSpinner } from 'react-icons/fa';
import { getStorage, ref, uploadBytes, getDownloadURL } from "firebase/storage";
import { useAuth } from '../../hooks/useAuth';
import api from '../../api/axiosInterceptor';

export default function EditBrandModal({ isOpen, onClose }) {
    const { currentUser, userProfile, refreshProfile } = useAuth();

    const [editFormData, setEditFormData] = useState({
        brand_name: '',
        logo_url: '',
        website_url: '',
        description: ''
    });
    const [logoFile, setLogoFile] = useState(null);
    const [logoPreview, setLogoPreview] = useState(null);
    const [isSavingBrand, setIsSavingBrand] = useState(false);

    // Initial load of form data when modal opens
    useEffect(() => {
        if (isOpen && userProfile?.brand_dna) {
            const dna = userProfile.brand_dna;
            setEditFormData({
                brand_name: dna.brand_name || '',
                logo_url: dna.logo_url || '',
                website_url: dna.website_url || '',
                description: dna.description || ''
            });
            setLogoPreview(dna.logo_url || null);
        }
    }, [isOpen, userProfile]);

    const handleEditLogoChange = (e) => {
        const file = e.target.files[0];
        if (file && (file.type === "image/png" || file.type === "image/svg+xml")) {
            setLogoFile(file);
            setLogoPreview(URL.createObjectURL(file));
        } else {
            alert("Please upload a high-quality PNG or SVG.");
        }
    };

    const handleSaveBrand = async () => {
        setIsSavingBrand(true);
        try {
            let finalLogoUrl = editFormData.logo_url;

            // Upload new logo if selected
            if (logoFile && currentUser) {
                const storage = getStorage();
                const storageRef = ref(storage, `users/${currentUser.uid}/brand/logo_${Date.now()}`);
                const uploadRes = await uploadBytes(storageRef, logoFile);
                finalLogoUrl = await getDownloadURL(uploadRes.ref);
            }

            await api.put('/auth/me/brand', {
                brand_name: editFormData.brand_name,
                logo_url: finalLogoUrl,
                website_url: editFormData.website_url,
                description: editFormData.description
            });

            await refreshProfile();
            onClose();
            setLogoFile(null);
        } catch (err) {
            console.error("Failed to update brand", err);
            alert("Failed to update brand. Please try again.");
        } finally {
            setIsSavingBrand(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4 animate-fade-in">
            <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden animate-scale-up">
                <div className="p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                    <h3 className="text-xl font-black text-slate-800 tracking-tight">Edit Brand Identity</h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <FaTimes size={20} />
                    </button>
                </div>

                <div className="p-8 space-y-6">

                    {/* Logo Upload */}
                    <div className="flex flex-col items-center">
                        <div className="relative group w-24 h-24 rounded-2xl border-2 border-dashed border-slate-200 hover:border-primary overflow-hidden flex items-center justify-center transition-all bg-slate-50 cursor-pointer">
                            <input type="file" accept=".png,.svg" className="absolute inset-0 opacity-0 cursor-pointer z-10" onChange={handleEditLogoChange} />
                            {logoPreview ? (
                                <img src={logoPreview} alt="Logo" className="w-full h-full object-contain p-2" />
                            ) : (
                                <FaCloudUploadAlt className="text-2xl text-slate-300 group-hover:text-primary transition-colors" />
                            )}
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white font-bold text-xs pointer-events-none">
                                Change
                            </div>
                        </div>
                        <span className="text-xs text-slate-400 font-bold mt-2 uppercase tracking-wide">Brand Logo</span>
                    </div>

                    {/* Brand Name Input */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">Brand Name</label>
                        <input
                            type="text"
                            value={editFormData.brand_name}
                            onChange={(e) => setEditFormData({ ...editFormData, brand_name: e.target.value })}
                            placeholder="Enter your brand name"
                            className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl font-bold text-slate-800 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                        />
                    </div>

                    {/* Website URL Input */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">Website URL</label>
                        <input
                            type="text"
                            value={editFormData.website_url}
                            onChange={(e) => setEditFormData({ ...editFormData, website_url: e.target.value })}
                            placeholder="https://your-website.com"
                            className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl text-slate-600 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                        />
                    </div>

                    {/* Description Input */}
                    <div className="space-y-2">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest pl-1">Brand Mission / Description</label>
                        <textarea
                            value={editFormData.description}
                            onChange={(e) => setEditFormData({ ...editFormData, description: e.target.value })}
                            placeholder="Briefly describe your brand's mission or vibe..."
                            rows={3}
                            className="w-full p-4 bg-slate-50 border border-slate-100 rounded-xl text-slate-600 focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none transition-all"
                        />
                    </div>

                    {/* Action Buttons */}
                    <div className="pt-4 flex gap-3">
                        <button
                            onClick={onClose}
                            className="flex-1 py-3.5 rounded-xl font-bold text-slate-500 bg-slate-100 hover:bg-slate-200 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleSaveBrand}
                            disabled={isSavingBrand || !editFormData.brand_name}
                            className="flex-1 py-3.5 rounded-xl font-bold text-white bg-primary hover:bg-blue-700 shadow-lg shadow-blue-500/30 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isSavingBrand ? <FaSpinner className="animate-spin" /> : "Save Changes"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
