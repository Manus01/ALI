import React from 'react';
import {
    FaCheckCircle, FaChevronDown, FaChevronUp, FaSpinner,
    FaRedo, FaDownload, FaTrash, FaTimes, FaExclamationTriangle
} from 'react-icons/fa';
import CarouselViewer from '../CarouselViewer';

/**
 * ChannelResultCard - Responsive channel result display with asset preview
 * Extracted from CampaignCenter.jsx for reusability
 */
export default function ChannelResultCard({
    channelId,
    channel,
    channelAssets,
    channelBlueprint,
    finalAssets,
    isExpanded,
    onToggle,
    approvedChannels,
    resultActionState,
    regeneratingId,
    primaryColor,
    // Actions
    onApproveAsset,
    onApproveAllChannelAssets,
    onRegenerateAllChannelAssets,
    onChannelExportZip,
    onOpenRejection,
    onDeleteAsset,
    onRegenerateFailed,
    getAssetContainerStyle
}) {
    const compatibilityWarning = finalAssets?.assets_metadata?.[channelId]?.compatibility_warning;
    const textCopy = channelBlueprint?.caption || channelBlueprint?.body ||
        (channelBlueprint?.headlines ? channelBlueprint.headlines.join(' | ') : '') ||
        channelBlueprint?.video_script || '';

    const channelActionState = resultActionState?.[channelId] || {};
    const pendingApprovals = channelAssets.filter(({ formatLabel }) => {
        const approvalKey = `${channelId}_${formatLabel}`;
        return !approvedChannels.includes(approvalKey);
    });
    const failedAssets = channelAssets.filter(({ url }) => !url || url === 'FAILED');
    const approvedChannelCount = approvedChannels.filter(key =>
        key === channelId || key.startsWith(`${channelId}_`)
    ).length;

    return (
        <div className="bg-white dark:bg-slate-800 rounded-xl sm:rounded-[2rem] border-2 border-slate-100 dark:border-slate-700 shadow-sm">
            {/* Channel Header - Responsive */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 sm:p-6 border-b border-slate-100 dark:border-slate-700">
                <div className="flex items-center gap-3">
                    <span className="text-xl sm:text-2xl">{channel.icon}</span>
                    <span className="font-black text-slate-800 dark:text-white text-base sm:text-lg">{channel.name}</span>
                    {finalAssets?.qc_reports?.[channelId]?.requires_review && (
                        <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300">
                            QC Review
                        </span>
                    )}
                    {compatibilityWarning && (
                        <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300 hidden sm:inline">
                            {compatibilityWarning}
                        </span>
                    )}
                </div>

                {/* Action Buttons - Scrollable on mobile */}
                <div className="flex items-center gap-2 text-xs overflow-x-auto pb-2 sm:pb-0 -mx-4 px-4 sm:mx-0 sm:px-0">
                    <span className="px-3 py-2 text-slate-400 dark:text-slate-500 whitespace-nowrap">
                        {finalAssets?.assets_metadata?.[channelId]?.size || 'Standard'}
                    </span>
                    <button
                        onClick={() => onApproveAllChannelAssets(channelId, channelAssets)}
                        disabled={pendingApprovals.length === 0 || channelActionState.approving}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-green-200 text-green-600 hover:bg-green-50 dark:border-green-800 dark:text-green-400 dark:hover:bg-green-900/30 transition-all disabled:opacity-50 whitespace-nowrap min-h-[40px]"
                    >
                        {channelActionState.approving ? <FaSpinner className="animate-spin" /> : <FaCheckCircle />}
                        Approve All
                    </button>
                    <button
                        onClick={() => onRegenerateAllChannelAssets(channelAssets, channelId)}
                        disabled={failedAssets.length === 0 || channelActionState.regenerating}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-amber-200 text-amber-600 hover:bg-amber-50 dark:border-amber-800 dark:text-amber-400 dark:hover:bg-amber-900/30 transition-all disabled:opacity-50 whitespace-nowrap min-h-[40px]"
                    >
                        {channelActionState.regenerating ? <FaSpinner className="animate-spin" /> : <FaRedo />}
                        Retry Failed
                    </button>
                    <button
                        onClick={() => onChannelExportZip(channelId)}
                        disabled={approvedChannelCount === 0 || channelActionState.exporting}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all disabled:opacity-50 whitespace-nowrap min-h-[40px]"
                    >
                        {channelActionState.exporting ? <FaSpinner className="animate-spin" /> : <FaDownload />}
                        Export
                    </button>
                    <button
                        onClick={onToggle}
                        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-all whitespace-nowrap min-h-[40px]"
                    >
                        {isExpanded ? <FaChevronUp /> : <FaChevronDown />}
                        <span className="hidden sm:inline">{isExpanded ? 'Collapse' : 'Expand'}</span>
                    </button>
                </div>
            </div>

            {/* Warning Banner */}
            {isExpanded && compatibilityWarning && (
                <div className="px-4 sm:px-6 pt-4">
                    <div className="flex items-center gap-2 text-xs font-bold text-red-600 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg sm:rounded-xl px-4 py-2">
                        <FaExclamationTriangle />
                        {compatibilityWarning}
                    </div>
                </div>
            )}

            {/* Content - Stacked on mobile, side-by-side on desktop */}
            {isExpanded && (
                <div className="flex flex-col lg:grid lg:grid-cols-2 gap-4 sm:gap-6 p-4 sm:p-6">
                    {/* Visual Assets */}
                    <div className="space-y-4">
                        <p className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Visual Assets</p>
                        <div className="space-y-4 sm:space-y-6">
                            {channelAssets.map(({ assetKey, formatLabel, url, draftId }) => (
                                <AssetPreview
                                    key={assetKey}
                                    channelId={channelId}
                                    channel={channel}
                                    assetKey={assetKey}
                                    formatLabel={formatLabel}
                                    url={url}
                                    draftId={draftId}
                                    approvedChannels={approvedChannels}
                                    regeneratingId={regeneratingId}
                                    onApproveAsset={onApproveAsset}
                                    onOpenRejection={onOpenRejection}
                                    onDeleteAsset={onDeleteAsset}
                                    onRegenerateFailed={onRegenerateFailed}
                                    getAssetContainerStyle={getAssetContainerStyle}
                                />
                            ))}
                        </div>
                    </div>

                    {/* Text Copy */}
                    <div className="space-y-4">
                        <p className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Text Copy</p>
                        <div className="bg-slate-50 dark:bg-slate-700 p-4 sm:p-5 rounded-xl sm:rounded-2xl border border-slate-100 dark:border-slate-600 min-h-[120px]">
                            <p className="text-slate-700 dark:text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">
                                {textCopy || 'No copy generated for this channel.'}
                            </p>
                        </div>

                        {/* Governance Summary */}
                        {(finalAssets?.qc_reports?.[channelId] || finalAssets?.claims_reports?.[channelId]) && (
                            <div className="bg-white dark:bg-slate-800 rounded-xl sm:rounded-2xl border border-slate-100 dark:border-slate-700 p-4 space-y-3">
                                <p className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">Governance</p>
                                {finalAssets?.qc_reports?.[channelId] && (
                                    <div className="text-xs text-slate-600 dark:text-slate-300 space-y-1">
                                        <div className="flex flex-wrap gap-1 sm:gap-2">
                                            {Object.entries(finalAssets.qc_reports[channelId].checks || {}).map(([check, detail]) => (
                                                <span
                                                    key={check}
                                                    className={`px-2 py-1 rounded-full text-[10px] font-bold uppercase ${detail.passes ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' : 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300'}`}
                                                >
                                                    {check.replace('_', ' ')}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Footer */}
            {isExpanded && (
                <div className="flex justify-between items-center p-4 sm:p-6 pt-0">
                    <div className="text-[10px] sm:text-xs text-slate-400 font-bold uppercase">
                        Review each format to approve, reject, or regenerate.
                    </div>
                </div>
            )}
        </div>
    );
}

/**
 * AssetPreview - Individual asset preview with actions
 */
function AssetPreview({
    channelId,
    channel,
    assetKey,
    formatLabel,
    url,
    draftId,
    approvedChannels,
    regeneratingId,
    onApproveAsset,
    onOpenRejection,
    onDeleteAsset,
    onRegenerateFailed,
    getAssetContainerStyle
}) {
    const approvalKey = `${channelId}_${formatLabel}`;
    const isApproved = approvedChannels.includes(approvalKey);

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{formatLabel}</span>
                {isApproved && (
                    <span className="text-[10px] font-black text-green-600 uppercase">Approved</span>
                )}
            </div>

            {/* Asset Display */}
            {Array.isArray(url) ? (
                <CarouselViewer slides={url} channelName={`${channel.name} ${formatLabel}`} />
            ) : (typeof url === 'string' && (url.endsWith('.html') || url.startsWith('data:text/html'))) ? (
                <div
                    className="bg-black rounded-xl sm:rounded-2xl overflow-hidden border border-slate-100 dark:border-slate-600 relative group"
                    style={getAssetContainerStyle(channelId)}
                >
                    <iframe
                        src={url}
                        title={`${channel.name} Motion`}
                        className="w-full h-full border-0 pointer-events-none"
                    />
                    <div className="absolute bottom-2 right-2 bg-black/60 text-white text-[10px] uppercase font-bold px-2 py-1 rounded backdrop-blur">
                        Motion
                    </div>
                </div>
            ) : url ? (
                <div
                    className="bg-slate-50 dark:bg-slate-700 rounded-xl sm:rounded-2xl overflow-hidden border border-slate-100 dark:border-slate-600"
                    style={getAssetContainerStyle(channelId)}
                >
                    <img src={url} alt={`${channel.name} ${formatLabel}`} className="w-full h-full object-contain" />
                </div>
            ) : (
                <div
                    className="bg-red-50 dark:bg-red-900/20 rounded-xl sm:rounded-2xl flex flex-col items-center justify-center border border-red-200 dark:border-red-800 gap-2"
                    style={{ ...getAssetContainerStyle(channelId), minHeight: '120px' }}
                >
                    <FaExclamationTriangle className="text-2xl sm:text-3xl text-red-400" />
                    <p className="text-red-500 text-xs font-bold uppercase">Generation Failed</p>
                </div>
            )}

            {/* Actions - Responsive */}
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                    {url && url !== 'FAILED' && (
                        <button
                            onClick={() => window.open(`/api/creatives/${draftId}/download`, '_blank')}
                            className="p-2 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-all min-h-[40px] min-w-[40px] flex items-center justify-center"
                            title="Download"
                        >
                            <FaDownload />
                        </button>
                    )}
                    <button
                        onClick={() => onDeleteAsset(draftId, assetKey, channelId)}
                        className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 transition-all min-h-[40px] min-w-[40px] flex items-center justify-center"
                        title="Delete"
                    >
                        <FaTrash />
                    </button>
                </div>

                {!isApproved && (
                    <div className="flex items-center gap-2">
                        {!url || url === 'FAILED' ? (
                            <>
                                <div className="flex items-center gap-2 text-red-400 font-bold text-xs px-3 py-2 bg-red-50 dark:bg-red-900/10 rounded-lg border border-red-100 dark:border-red-900/20">
                                    <FaExclamationTriangle /> Failed
                                </div>
                                <button
                                    onClick={() => onRegenerateFailed(draftId)}
                                    disabled={regeneratingId === draftId}
                                    className="px-3 sm:px-4 py-2 rounded-lg sm:rounded-xl font-bold text-amber-600 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-all flex items-center gap-2 disabled:opacity-50 min-h-[40px] text-xs sm:text-sm"
                                >
                                    {regeneratingId === draftId ? (
                                        <><FaSpinner className="animate-spin" /> <span className="hidden sm:inline">Regenerating...</span></>
                                    ) : (
                                        <><FaRedo /> Retry</>
                                    )}
                                </button>
                            </>
                        ) : (
                            <>
                                <button
                                    onClick={() => onOpenRejection(channelId, formatLabel, draftId, assetKey)}
                                    className="px-3 sm:px-5 py-2 sm:py-3 rounded-lg sm:rounded-xl font-bold text-red-600 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/50 transition-all flex items-center gap-2 min-h-[40px] text-xs sm:text-sm"
                                >
                                    <FaTimes /> Reject
                                </button>
                                <button
                                    onClick={() => onApproveAsset(channelId, formatLabel)}
                                    className="px-4 sm:px-6 py-2 sm:py-3 rounded-lg sm:rounded-xl font-bold text-white bg-green-600 hover:bg-green-700 transition-all flex items-center gap-2 shadow-lg min-h-[40px] text-xs sm:text-sm"
                                >
                                    <FaCheckCircle /> Approve
                                </button>
                            </>
                        )}
                    </div>
                )}

                {isApproved && (
                    <div className="flex items-center gap-2 text-green-600 dark:text-green-400 font-bold text-sm">
                        <FaCheckCircle /> Approved
                    </div>
                )}
            </div>
        </div>
    );
}
