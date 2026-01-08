/**
 * ALI Enterprise Application - Tutorial Lifecycle Types
 * Spec v2.2 Tutorial Generation §7: Draft → Review → Publish Workflow
 */

export type TutorialStatus = 'DRAFT' | 'IN_REVIEW' | 'PUBLISHED' | 'ARCHIVED';

export type TutorialRequestStatus =
    | 'PENDING'
    | 'APPROVED'
    | 'DENIED'
    | 'GENERATING'
    | 'COMPLETED'
    | 'FAILED';

export interface TutorialVersion {
    versionId: string;
    hash: string;
    timestamp: string;
    modelVersion: string;
    publishedBy?: string;
}

export interface RubricScore {
    dimension: string;
    score: number;
    passed: boolean;
    issues: string[];
}

export interface RubricReport {
    verdict: 'PASS' | 'FAIL';
    overallScore: number;
    scores: RubricScore[];
    citationCoverage: number;
    cardWordCountViolations: number;
    syntaxErrors: string[];
    fixList: string[];
    validatedAt: string;
}

export interface TutorialRequest {
    requestId: string;
    userId: string;
    userEmail: string;
    topic: string;
    context?: string;
    status: TutorialRequestStatus;
    createdAt: Date;
    adminDecision?: {
        action: 'approved' | 'denied';
        approvedBy?: string;
        deniedBy?: string;
        approvedAt?: Date;
        deniedAt?: Date;
        reason?: string;
    };
    tutorialId?: string;
}
