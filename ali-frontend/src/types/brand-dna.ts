/**
 * ALI Enterprise Application - Brand DNA Pack Interface
 * Spec v2.2 Advertising §6: Mandatory Governance Layer
 */

export interface VisualRules {
    /** HEX color values for brand palette */
    colorPalette: string[];
    /** Typography configuration */
    typography: {
        headingFont: string;
        bodyFont: string;
        sizes: Record<string, string>;
    };
    /** Spacing tokens */
    spacing: Record<string, string>;
    /** Corner radius for UI elements */
    cornerRadius: string;
}

export interface BrandDNAPack {
    packId: string;
    userId: string;

    /** Visual identity rules */
    visualRules: VisualRules;

    /** 3-5 signature SVG pattern sets (waves, diagonals, frames) */
    brandMotifs: string[];

    /** Voice and messaging guidelines */
    toneOfVoice: {
        formality: 'casual' | 'professional' | 'formal';
        vocabulary: string[];
        bannedPhrases: string[];
    };

    /** Claims verification requirements */
    claimsPolicy: {
        /** Claims requiring proof */
        requireProof: string[];
        /** Claims to auto-rewrite to safe phrasing */
        autoRewrite: string[];
    };

    /** Visual and copy constraints */
    dosDonts: Array<{
        type: 'do' | 'dont';
        category: 'visual' | 'copy';
        example: string;
    }>;

    createdAt: Date;
    updatedAt: Date;
}
