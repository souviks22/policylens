export type ChangeType = "addition" | "deletion" | "modification" | "regulatory_update" | "unchanged";
export type ImpactLevel = "high" | "medium" | "low" | "none";

export interface UploadResponse {
  file_id: string;
  filename: string;
  pages: number;
  word_count: number;
  status: string;
}

export interface DiffChunk {
  id: string;
  type: ChangeType;
  old_text: string | null;
  new_text: string | null;
  section: string | null;
  line_start: number | null;
  line_end: number | null;
}

export interface SemanticChange {
  id: string;
  change_type: ChangeType;
  summary: string;
  old_content: string | null;
  new_content: string | null;
  section: string | null;
  business_impact: string;
  compliance_impact: string;
  regulatory_impact: string;
  impact_level: ImpactLevel;
  explanation: string;
  recommendations: string[];
}

export interface DocumentStats {
  total_pages: number;
  total_words: number;
  total_characters: number;
  sections_detected: string[];
}

export interface ComparisonSummary {
  total_changes: number;
  additions: number;
  deletions: number;
  modifications: number;
  regulatory_updates: number;
  overall_impact_level: ImpactLevel;
  executive_summary: string;
  key_changes: string[];
  risk_areas: string[];
  compliance_flags: string[];
}

export interface SectionMatch {
  id: string;
  doc1_section: string | null;
  doc2_section: string | null;
  doc1_content: string | null;
  doc2_content: string | null;
  similarity_score: number;
  match_type: "unchanged" | "modified" | "added" | "deleted";
  doc1_index: number | null;
  doc2_index: number | null;
}

export interface SectionAnalysis {
  matches: SectionMatch[];
  similarity_matrix: number[][];
  doc1_section_labels: string[];
  doc2_section_labels: string[];
  overall_structural_similarity: number;
  semantic_clone_pairs: string[][];
}

export interface Annotation {
  id: string;
  comparison_id: string;
  change_id: string;
  change_type: string | null;
  author: string;
  text: string;
  resolved: boolean;
  created_at: string;
}

export interface ComparisonListItem {
  id: string;
  doc1_name: string;
  doc2_name: string;
  total_changes: number;
  additions: number;
  deletions: number;
  modifications: number;
  overall_impact: string;
  structural_similarity: number;
  created_at: string;
}

export interface ComparisonResult {
  comparison_id: string;
  doc1_name: string;
  doc2_name: string;
  doc1_stats: DocumentStats;
  doc2_stats: DocumentStats;
  diff_chunks: DiffChunk[];
  semantic_changes: SemanticChange[];
  summary: ComparisonSummary;
  doc1_content: string;
  doc2_content: string;
  doc1_sections: string[];
  doc2_sections: string[];
  section_analysis: SectionAnalysis | null;
  text_similarity_ratio: number;
}

export type AppStep = "upload" | "analyzing" | "results";

export interface UploadedDoc {
  file_id: string;
  filename: string;
  pages: number;
  word_count: number;
}
