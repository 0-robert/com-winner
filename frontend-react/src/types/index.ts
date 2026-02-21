export type ContactStatus = 'active' | 'inactive' | 'unknown' | 'opted_out';

export interface Contact {
    id: string;
    name: string;
    email: string;
    title: string;
    organization: string;
    status: ContactStatus;
    needs_human_review: boolean;
    review_reason: string | null;
    district_website: string | null;
    linkedin_url: string | null;
    created_at: string;
    updated_at: string;
}

export interface VerificationResult {
    id: string;
    contact_id: string;
    status: ContactStatus;
    needs_human_review: boolean;
    review_reason: string | null;
    api_costs_usd: number;
    tokens_used: number;
    labor_hours_saved: number;
    estimated_value_usd: number;
    timestamp: string;
}

export interface ValueProofReceipt {
    contacts_processed: number;
    replacements_found: number;
    flagged_for_review: number;
    contacts_verified_active: number;
    contacts_marked_inactive: number;
    total_api_cost_usd: number;
    total_value_generated_usd: number;
    total_labor_hours_saved: number;
    total_tokens_used: number;
    net_roi_percentage: number;
    simulated_invoice_usd: number;
    cost_per_contact_usd: number;
    cost_per_replacement_usd: number;
}
