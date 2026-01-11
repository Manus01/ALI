import api from '../api/axiosInterceptor';

export const fetchKnowledgePacks = async ({ topicTags } = {}) => {
    const params = {};
    if (topicTags?.length) {
        params.topic_tags = topicTags.join(',');
    }
    const response = await api.get('/ai/web/packs', { params });
    return response.data;
};

export const fetchMonitoringAlerts = async ({ severity } = {}) => {
    const params = {};
    if (severity?.length) {
        params.severity = severity.join(',');
    }
    const response = await api.get('/ai/web/monitor/alerts', { params });
    return response.data;
};

export const queryKnowledge = async ({ queryText, topK = 10, threshold = 0.78, topicFilter, minCredibilityScore }) => {
    const response = await api.post('/ai/web/knowledge/query', {
        queryText,
        topK,
        threshold,
        topicFilter,
        minCredibilityScore
    });
    return response.data;
};
