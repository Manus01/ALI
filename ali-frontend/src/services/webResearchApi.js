import { apiClient, unwrapOrThrow } from '../lib/api-client';

export const fetchKnowledgePacks = async ({ topicTags } = {}) => {
    const queryParams = {};
    if (topicTags?.length) {
        queryParams.topic_tags = topicTags.join(',');
    }
    const result = await apiClient.get('/ai/web/packs', { queryParams });
    return unwrapOrThrow(result);
};

export const fetchMonitoringAlerts = async ({ severity } = {}) => {
    const queryParams = {};
    if (severity?.length) {
        queryParams.severity = severity.join(',');
    }
    const result = await apiClient.get('/ai/web/monitor/alerts', { queryParams });
    return unwrapOrThrow(result);
};

export const queryKnowledge = async ({ queryText, topK = 10, threshold = 0.78, topicFilter, minCredibilityScore }) => {
    const result = await apiClient.post('/ai/web/knowledge/query', {
        body: {
            queryText,
            topK,
            threshold,
            topicFilter,
            minCredibilityScore
        }
    });
    return unwrapOrThrow(result);
};
