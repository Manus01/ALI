import React, { useState } from 'react';
import { FaArrowLeft, FaArrowRight } from 'react-icons/fa';

/**
 * CarouselViewer - A reusable component for displaying image carousels
 * Extracted from CampaignCenter.jsx for better maintainability
 */
const CarouselViewer = ({ slides, channelName }) => {
    const [index, setIndex] = useState(0);

    if (!slides || slides.length === 0) {
        return null;
    }

    return (
        <div className="rounded-2xl overflow-hidden border border-slate-100 dark:border-slate-600 relative group aspect-square max-w-sm mx-auto bg-slate-50 dark:bg-slate-700">
            <img src={slides[index]} alt={`${channelName} Slide ${index + 1}`} className="w-full h-full object-cover" />

            {/* Controls */}
            {slides.length > 1 && (
                <>
                    <div className="absolute inset-0 flex items-center justify-between p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                            onClick={(e) => { e.stopPropagation(); setIndex(prev => prev > 0 ? prev - 1 : slides.length - 1); }}
                            className="w-8 h-8 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur flex items-center justify-center hover:scale-110 transition-transform shadow-sm"
                            aria-label="Previous slide"
                        >
                            <FaArrowLeft className="text-xs text-slate-800 dark:text-white" />
                        </button>
                        <button
                            onClick={(e) => { e.stopPropagation(); setIndex(prev => prev < slides.length - 1 ? prev + 1 : 0); }}
                            className="w-8 h-8 rounded-full bg-white/80 dark:bg-slate-800/80 backdrop-blur flex items-center justify-center hover:scale-110 transition-transform shadow-sm"
                            aria-label="Next slide"
                        >
                            <FaArrowRight className="text-xs text-slate-800 dark:text-white" />
                        </button>
                    </div>
                    {/* Indicators */}
                    <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-1.5 pointer-events-none">
                        {slides.map((_, i) => (
                            <div
                                key={i}
                                className={`w-1.5 h-1.5 rounded-full transition-all shadow-sm ${i === index ? 'bg-white scale-125' : 'bg-white/50'}`}
                            />
                        ))}
                    </div>
                    {/* Counter Badge */}
                    <div className="absolute top-3 right-3 bg-black/50 backdrop-blur text-white text-[10px] font-black px-2 py-1 rounded-full pointer-events-none">
                        {index + 1} / {slides.length}
                    </div>
                </>
            )}
        </div>
    );
};

export default CarouselViewer;
