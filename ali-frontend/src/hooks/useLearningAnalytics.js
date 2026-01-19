/**
 * Learning Analytics Hook
 * Tracks user interactions for the Adaptive Tutorial Engine (ATE).
 * 
 * Events tracked:
 * - Section navigation (section_start, section_complete)
 * - Quiz interactions (quiz_attempt, quiz_pass, quiz_fail)
 * - Media interactions (audio_play, video_play)
 * - Time spent per section
 */
import { useCallback, useRef, useEffect } from 'react';
import { apiClient } from '../lib/api-client';

// Generate a session ID once per page load
const SESSION_ID = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Detect device type
const getDeviceType = () => {
    const width = window.innerWidth;
    if (width < 768) return 'mobile';
    if (width < 1024) return 'tablet';
    return 'desktop';
};

/**
 * Hook for tracking learning analytics events.
 * 
 * @param {Object} options
 * @param {string} options.tutorialId - Current tutorial ID
 * @param {string} options.tutorialTopic - Tutorial topic
 * @param {string} options.tutorialCategory - Tutorial category
 */
export function useLearningAnalytics({ tutorialId, tutorialTopic, tutorialCategory }) {
    const sectionStartTime = useRef(null);
    const currentSectionIndex = useRef(null);
    const eventQueue = useRef([]);
    const flushTimer = useRef(null);

    // Flush events in batch (more efficient than individual requests)
    const flushEvents = useCallback(async () => {
        if (eventQueue.current.length === 0) return;

        const events = [...eventQueue.current];
        eventQueue.current = [];

        try {
            await apiClient('/learning-analytics/events/batch', {
                method: 'POST',
                body: JSON.stringify({ events })
            });
        } catch (error) {
            // Silently fail - analytics should not interrupt user experience
            console.warn('[LearningAnalytics] Failed to flush events:', error);
            // Re-queue events for retry
            eventQueue.current = [...events, ...eventQueue.current];
        }
    }, []);

    // Queue an event for batch sending
    const queueEvent = useCallback((eventType, data = {}) => {
        const event = {
            event_type: eventType,
            tutorial_id: tutorialId,
            tutorial_topic: tutorialTopic,
            tutorial_category: tutorialCategory,
            device_type: getDeviceType(),
            session_id: SESSION_ID,
            ...data
        };

        eventQueue.current.push(event);

        // Auto-flush after 5 seconds or 10 events
        if (eventQueue.current.length >= 10) {
            flushEvents();
        } else if (!flushTimer.current) {
            flushTimer.current = setTimeout(() => {
                flushEvents();
                flushTimer.current = null;
            }, 5000);
        }
    }, [tutorialId, tutorialTopic, tutorialCategory, flushEvents]);

    // Track section start
    const trackSectionStart = useCallback((sectionIndex, sectionTitle) => {
        // If there was a previous section, log the time spent
        if (currentSectionIndex.current !== null && sectionStartTime.current) {
            const timeSpent = Math.round((Date.now() - sectionStartTime.current) / 1000);
            queueEvent('section_complete', {
                section_index: currentSectionIndex.current,
                time_spent_seconds: timeSpent
            });
        }

        // Start tracking new section
        currentSectionIndex.current = sectionIndex;
        sectionStartTime.current = Date.now();

        queueEvent('section_start', {
            section_index: sectionIndex,
            section_title: sectionTitle
        });
    }, [queueEvent]);

    // Track quiz attempt
    const trackQuizAttempt = useCallback((sectionIndex, score, passed) => {
        queueEvent(passed ? 'quiz_pass' : 'quiz_fail', {
            section_index: sectionIndex,
            quiz_score: score
        });
    }, [queueEvent]);

    // Track media play
    const trackMediaPlay = useCallback((mediaType, sectionIndex) => {
        queueEvent(mediaType === 'audio' ? 'audio_play' : 'video_play', {
            section_index: sectionIndex
        });
    }, [queueEvent]);

    // Track scroll depth
    const trackScrollDepth = useCallback((sectionIndex, depthPercent) => {
        queueEvent('scroll_depth', {
            section_index: sectionIndex,
            scroll_depth_percent: depthPercent
        });
    }, [queueEvent]);

    // Track help click
    const trackHelpClick = useCallback((sectionIndex) => {
        queueEvent('help_click', {
            section_index: sectionIndex
        });
    }, [queueEvent]);

    // Flush events when component unmounts or tutorial changes
    useEffect(() => {
        return () => {
            // Log final section completion
            if (currentSectionIndex.current !== null && sectionStartTime.current) {
                const timeSpent = Math.round((Date.now() - sectionStartTime.current) / 1000);
                queueEvent('section_complete', {
                    section_index: currentSectionIndex.current,
                    time_spent_seconds: timeSpent
                });
            }

            // Clear timer and flush remaining events
            if (flushTimer.current) {
                clearTimeout(flushTimer.current);
            }
            flushEvents();
        };
    }, [tutorialId, queueEvent, flushEvents]);

    return {
        trackSectionStart,
        trackQuizAttempt,
        trackMediaPlay,
        trackScrollDepth,
        trackHelpClick,
        flushEvents
    };
}

export default useLearningAnalytics;
