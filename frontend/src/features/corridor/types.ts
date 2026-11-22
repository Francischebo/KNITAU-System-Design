/**
 * Contract Mirror of backend/apps/corridor/api/serializers.py
 * In day-to-day sprints, run `make codegen-api` to regenerate these directly
 * from backend/openapi-schema.yaml (Single Source of Truth).
 */
export type SimilarityLabel = 'Strong Match' | 'Partial Match' | 'General Mentor';

export interface DiasporaMentorMatch {
  id: string;
  full_name: string;
  country: string;
  sector: string;
  role_title: string;
  bio: string;
  expertise_tags: string[];
  is_verified: boolean;
  similarity_score: number;
  similarity_label: SimilarityLabel;
  matched_tags: string[];
  matched_skills: string[];
}

export interface CreateDiasporaMentorInput {
  full_name: string;
  country: string;
  sector: string;
  role_title: string;
  bio: string;
  expertise_tags: string[];
  capacity?: number;
  auto_verify?: boolean;
}
