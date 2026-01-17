import React from 'react';
import {
    FaPalette, FaCheckCircle, FaChevronDown, FaChevronUp,
    FaSpinner, FaRedo, FaDownload, FaTrash, FaExclamationTriangle
} from 'react-icons/fa';

/**
 * AssetLibrary - Responsive asset library view with collapsible campaign groups
 * Extracted from CampaignCenter.jsx for reusability
 */
export default function AssetLibrary({
    libraryTab,
    setLibraryTab,
    pendingCampaigns,
    approvedCampaigns,
    expandedGroups,
    setExpandedGroups,
    loadingDrafts,
    publishingId,
    remixingId,
    regeneratingId,
    onApproveAndPublish,
    onRemix,
    onDeleteAsset,
    onRegenerateFailed,
    onReview
}) {
    const campaignsToShow = libraryTab === 'pending' ? pendingCampaigns : approvedCampaigns;

    const toggleGroup = (groupName) => {
        setExpandedGroups(prev => ({
            ...prev,
            [groupName]: expandedGroups[groupName] === false ? true : false
        }));
    };

    if (loadingDrafts) {
        return (
            <div className="flex items-center justify-center py-20">
                <FaSpinner className="animate-spin text-2xl text-slate-400" />
            </div>
        );
    }

    return (
        <div className="space-y-4 animate-fade-in">
            {/* Library Sub-Tabs - Responsive */}
            <div className="flex justify-center mb-4 sm:mb-6">
                <div className="bg-slate-50 dark:bg-slate-800 p-1 rounded-lg sm:rounded-xl inline-flex border border-slate-200 dark:border-slate-600 w-full sm:w-auto">
                    <button
                        onClick={() => setLibraryTab('pending')}
                        className={`flex-1 sm:flex-none px-3 sm:px-5 py-2 sm:py-1.5 rounded-md sm:rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 min-h-[44px] sm:min-h-0 ${libraryTab === 'pending'
                                ? 'bg-amber-500 text-white shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                    >
                        <span>⏳</span> <span className="hidden sm:inline">Pending</span> Approval
                    </button>
                    <button
                        onClick={() => setLibraryTab('approved')}
                        className={`flex-1 sm:flex-none px-3 sm:px-5 py-2 sm:py-1.5 rounded-md sm:rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2 min-h-[44px] sm:min-h-0 ${libraryTab === 'approved'
                                ? 'bg-green-500 text-white shadow-sm'
                                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                    >
                        <FaCheckCircle className="text-xs" /> Approved
                    </button>
                </div>
            </div>

            {/* Empty State */}
            {campaignsToShow.length === 0 && (
                <div className="text-center py-12 sm:py-16 bg-white dark:bg-slate-800 rounded-xl sm:rounded-2xl border border-slate-100 dark:border-slate-700">
                    <div className="text-3xl sm:text-4xl mb-4">{libraryTab === 'pending' ? '✨' : '📭'}</div>
                    <h3 className="text-base sm:text-lg font-bold text-slate-700 dark:text-slate-300 mb-2">
                        {libraryTab === 'pending' ? 'No Pending Campaigns' : 'No Approved Campaigns Yet'}
                    </h3>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                        {libraryTab === 'pending'
                            ? 'All your campaigns have been reviewed and approved!'
                            : 'Start by creating a campaign and approving your assets.'}
                    </p>
                </div>
            )}

            {/* Campaign Groups */}
            {campaignsToShow.map(([groupName, assets]) => {
                const isExpanded = expandedGroups[groupName] !== false;
                const pendingCount = assets.filter(a => a.status === 'DRAFT').length;
                const publishedCount = assets.filter(a => a.status === 'PUBLISHED').length;

                return (
                    <div key={groupName} className="bg-white dark:bg-slate-800 rounded-xl sm:rounded-2xl border border-slate-100 dark:border-slate-700 overflow-hidden shadow-sm">
                        {/* Collapsible Header */}
                        <button
                            onClick={() => toggleGroup(groupName)}
                            className="w-full bg-slate-50 dark:bg-slate-900/50 p-4 sm:p-5 border-b border-slate-100 dark:border-slate-700 flex justify-between items-center hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                        >
                            <div className="flex items-center gap-3 sm:gap-4 flex-1 min-w-0">
                                <div className={`p-2 rounded-lg transition-all flex-shrink-0 ${isExpanded ? 'bg-primary/10 text-primary' : 'bg-slate-200 dark:bg-slate-700 text-slate-400'}`}>
                                    {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
                                </div>
                                <div className="text-left min-w-0">
                                    <h3 className="font-black text-slate-800 dark:text-white text-sm sm:text-base truncate" title={groupName}>
                                        {groupName}
                                    </h3>
                                    <p className="text-[10px] sm:text-xs text-slate-400 font-bold uppercase tracking-wider mt-0.5">
                                        {assets.length} {assets.length === 1 ? 'asset' : 'assets'} • {new Date(assets[0].createdAt).toLocaleDateString()}
                                    </p>
                                </div>
                            </div>
                            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
                                {pendingCount > 0 && (
                                    <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400">
                                        {pendingCount}
                                    </span>
                                )}
                                {publishedCount > 0 && (
                                    <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-green-100 dark:bg-green-900/50 text-green-600 dark:text-green-400">
                                        {publishedCount}
                                    </span>
                                )}
                            </div>
                        </button>

                        {/* Collapsible Content - Responsive Grid */}
                        {isExpanded && (
                            <div className="p-4 sm:p-6 animate-fade-in">
                                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                                    {assets.map(asset => (
                                        <AssetCard
                                            key={asset.id}
                                            asset={asset}
                                            publishingId={publishingId}
                                            remixingId={remixingId}
                                            regeneratingId={regeneratingId}
                                            onApproveAndPublish={onApproveAndPublish}
                                            onRemix={onRemix}
                                            onDeleteAsset={onDeleteAsset}
                                            onRegenerateFailed={onRegenerateFailed}
                                            onReview={onReview}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

/**
 * AssetCard - Individual asset display with responsive layout
 */
function AssetCard({
    asset,
    publishingId,
    remixingId,
    regeneratingId,
    onApproveAndPublish,
    onRemix,
    onDeleteAsset,
    onRegenerateFailed,
    onReview
}) {
    const createdAt = asset.createdAt?.seconds
        ? new Date(asset.createdAt.seconds * 1000)
        : new Date(asset.createdAt || Date.now());

    const statusColors = {
        PUBLISHED: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
        FAILED: 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300',
        DRAFT: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
    };

    return (
        <div className="border border-slate-100 dark:border-slate-700 rounded-xl sm:rounded-2xl bg-white dark:bg-slate-800/60 p-4 sm:p-5 flex flex-col">
            {/* Header */}
            <div className="flex items-start gap-3 mb-3">
                <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-lg sm:rounded-xl bg-white dark:bg-slate-700 border border-slate-100 dark:border-slate-600 overflow-hidden flex items-center justify-center flex-shrink-0">
                    {asset.thumbnailUrl ? (
                        <img src={asset.thumbnailUrl} alt={asset.title} className="h-full w-full object-cover" />
                    ) : (
                        <FaPalette className="text-lg sm:text-xl text-slate-300" />
                    )}
                </div>
                <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-slate-800 dark:text-white text-sm truncate">{asset.title || 'Untitled'}</h4>
                    <p className="text-[10px] sm:text-[11px] text-slate-400 font-bold uppercase tracking-wider">
                        {asset.channel || 'Asset'} • {asset.format || 'Format'}
                    </p>
                </div>
            </div>

            {/* Preview */}
            <div className="aspect-video bg-slate-50 dark:bg-slate-700/40 rounded-lg sm:rounded-xl border border-slate-100 dark:border-slate-600 overflow-hidden mb-3">
                {asset.thumbnailUrl ? (
                    <img src={asset.thumbnailUrl} alt={asset.title} className="w-full h-full object-cover" />
                ) : (
                    <div className="w-full h-full flex items-center justify-center">
                        <FaPalette className="text-2xl text-slate-300" />
                    </div>
                )}
            </div>

            {/* Status & Date */}
            <div className="flex items-center justify-between mb-3">
                <span className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${statusColors[asset.status] || statusColors.DRAFT}`}>
                    {asset.status === 'PUBLISHED' ? 'Approved' : asset.status === 'FAILED' ? 'Failed' : 'Draft'}
                </span>
                <span className="text-[10px] sm:text-[11px] text-slate-400 font-semibold">
                    {createdAt.toLocaleDateString()}
                </span>
            </div>

            {/* Actions - Touch-friendly */}
            <div className="flex flex-wrap gap-2 mt-auto">
                {asset.status === 'DRAFT' && (
                    <button
                        onClick={() => onApproveAndPublish(asset.id)}
                        disabled={publishingId === asset.id}
                        className="flex-1 px-3 py-2 rounded-lg bg-green-600 text-white text-xs font-bold hover:bg-green-700 transition-all disabled:opacity-50 min-h-[44px] flex items-center justify-center gap-2"
                    >
                        {publishingId === asset.id ? <FaSpinner className="animate-spin" /> : <FaCheckCircle />}
                        Approve
                    </button>
                )}
                {asset.status === 'FAILED' && (
                    <button
                        onClick={() => onRegenerateFailed(asset.id)}
                        disabled={regeneratingId === asset.id}
                        className="flex-1 px-3 py-2 rounded-lg bg-amber-500 text-white text-xs font-bold hover:bg-amber-600 transition-all disabled:opacity-50 min-h-[44px] flex items-center justify-center gap-2"
                    >
                        {regeneratingId === asset.id ? <FaSpinner className="animate-spin" /> : <FaRedo />}
                        Retry
                    </button>
                )}
                {asset.campaignId && (
                    <button
                        onClick={() => onReview(asset)}
                        className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300 text-xs font-bold hover:bg-slate-50 dark:hover:bg-slate-700 transition-all min-h-[44px]"
                    >
                        Review
                    </button>
                )}
                <button
                    onClick={() => onDeleteAsset(asset.id)}
                    className="px-3 py-2 rounded-lg text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all min-h-[44px]"
                    title="Delete"
                >
                    <FaTrash />
                </button>
            </div>
        </div>
    );
}
