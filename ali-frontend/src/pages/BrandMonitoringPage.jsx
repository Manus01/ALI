import React from 'react';
import BrandMonitoringDashboard from '../components/BrandMonitoringDashboard';

/**
 * Brand Monitoring Page
 * 
 * Redesigned as self-contained dashboard with:
 * - Brand Health Score (0-100)
 * - Geographic Sentiment Insights
 * - Priority Actions (urgency-scored threats)
 * - Platform Reporting Guidance
 * - Sources Overview
 * 
 * Powered by 28 API endpoints and hourly automated scanning.
 */
export default function BrandMonitoringPage() {
    return <BrandMonitoringDashboard />;
}
