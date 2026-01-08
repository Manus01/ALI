/**
 * ALI Enterprise Application - Knowledge Pack / Truth Source JSON
 * Spec v2.5 Web Search §5: Knowledge Pack Schema
 */

export interface CitationObject {
    url: string;
    domain: string;
    title: string;
    author?: string;
    publishedAt?: string;
    retrievedAt: string;
    /** Short excerpt supporting the fact */
    supportingQuote: string;
    /** Where the quote appears in the source */
    quoteContext: string;
    /** Confidence in fact accuracy (0-100) */
    confidenceScore: number;
    /** Source authority score (0-100) */
    credibilityScore: number;
    licenseNotes?: string;
}

export interface ExtractedFact {
    factId: string;
    text: string;
    citation: CitationObject;
    topicTags: string[];
    confidenceScore: number;
}

export interface KnowledgePackSource {
    url: string;
    domain: string;
    title: string;
    credibilityScore: number;
    retrievedAt: string;
}

export interface KnowledgePackChange {
    date: string;
    summary: string;
    severity: 'CRITICAL' | 'IMPORTANT' | 'INFORMATIONAL';
}

export interface KnowledgePack {
    packId: string;
    topicTags: string[];
    createdAt: Date;
    /** When pack must be refreshed */
    validUntil: Date;
    /** How rapidly the topic changes (0-100) */
    volatilityScore: number;

    /** Source metadata */
    sources: KnowledgePackSource[];

    /** Extracted facts with citations */
    facts: ExtractedFact[];

    /** Reference to vector embeddings for RAG */
    embeddingsRef?: string;

    /** Change history for monitored packs */
    changeLog: KnowledgePackChange[];
}
