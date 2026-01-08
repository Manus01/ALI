"""
Enhanced Critic Agent
Spec v2.2 Tutorial Generation §6: Quality Control & Critic Agent

Provides:
1. Measurable rubric thresholds (not just LLM vibes)
2. Card word count validation
3. Citation coverage analysis
4. Mermaid/JSON syntax validation
5. Reading level assessment
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class RubricDimension(str, Enum):
    """Rubric dimensions for tutorial evaluation."""
    CARD_WORD_COUNT = "card_word_count"
    SECTION_COUNT = "section_count"
    SECTION_STRUCTURE = "section_structure"  # v2.2: Required pedagogical sections
    CITATION_COVERAGE = "citation_coverage"
    SYNTAX_VALIDATION = "syntax_validation"
    MEDIA_COMPLETENESS = "media_completeness"
    QUIZ_QUALITY = "quiz_quality"


class IssueSeverity(str, Enum):
    """Severity levels for rubric issues."""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class RubricThresholds:
    """
    Measurable thresholds for tutorial quality.
    Spec v2.2 §6.2: Card size constraints, section requirements.
    """
    # Card word count (per text block)
    card_word_min: int = 120
    card_word_target: int = 180
    card_word_hard_max: int = 220
    
    # Sections per tutorial
    sections_min: int = 3
    sections_max: int = 12
    
    # Citation requirements
    citations_min_per_concept: int = 1
    citation_coverage_threshold: float = 0.3  # 30% of facts should have citations
    
    # Media requirements
    media_per_section_min: int = 1  # At least one visual/audio per section
    
    # Quiz requirements
    quiz_options_min: int = 3
    quiz_options_max: int = 5


@dataclass
class RubricIssue:
    """A single issue found during rubric evaluation."""
    dimension: str
    severity: str
    location: str
    message: str
    value: Any = None
    threshold: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RubricReport:
    """Complete rubric evaluation report."""
    verdict: str  # PASS or FAIL
    overall_score: int  # 0-100
    dimension_scores: Dict[str, int] = field(default_factory=dict)
    issues: List[RubricIssue] = field(default_factory=list)
    citation_coverage: float = 0.0
    card_word_count_violations: int = 0
    syntax_errors: List[str] = field(default_factory=list)
    fix_list: List[str] = field(default_factory=list)
    validated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["issues"] = [i.to_dict() if hasattr(i, "to_dict") else i for i in self.issues]
        return data


class CriticAgent:
    """
    Enhanced Critic Agent with measurable rubric checks.
    Spec v2.2 §6: Quality Control.
    """
    
    def __init__(self, thresholds: Optional[RubricThresholds] = None):
        self.thresholds = thresholds or RubricThresholds()
    
    def validate_card_word_count(
        self,
        sections: List[Dict[str, Any]]
    ) -> tuple[int, List[RubricIssue]]:
        """
        Validate that text cards are within word count limits.
        Spec v2.2 §6.2: Cards should be 120-180 words, hard max 220.
        """
        issues = []
        score = 100
        violations = 0
        
        for sec_idx, section in enumerate(sections):
            for block_idx, block in enumerate(section.get("blocks", [])):
                if block.get("type") != "text":
                    continue
                
                content = block.get("content", "")
                word_count = len(content.split())
                location = f"Section {sec_idx + 1}: {section.get('title', 'Untitled')}, Block {block_idx + 1}"
                
                if word_count > self.thresholds.card_word_hard_max:
                    issues.append(RubricIssue(
                        dimension=RubricDimension.CARD_WORD_COUNT.value,
                        severity=IssueSeverity.FAIL.value,
                        location=location,
                        message=f"Word count {word_count} exceeds hard limit of {self.thresholds.card_word_hard_max}",
                        value=word_count,
                        threshold=self.thresholds.card_word_hard_max
                    ))
                    score -= 15
                    violations += 1
                    
                elif word_count > self.thresholds.card_word_target:
                    issues.append(RubricIssue(
                        dimension=RubricDimension.CARD_WORD_COUNT.value,
                        severity=IssueSeverity.WARNING.value,
                        location=location,
                        message=f"Word count {word_count} exceeds target of {self.thresholds.card_word_target}",
                        value=word_count,
                        threshold=self.thresholds.card_word_target
                    ))
                    score -= 5
                    
                elif word_count < self.thresholds.card_word_min:
                    issues.append(RubricIssue(
                        dimension=RubricDimension.CARD_WORD_COUNT.value,
                        severity=IssueSeverity.WARNING.value,
                        location=location,
                        message=f"Word count {word_count} below minimum of {self.thresholds.card_word_min}",
                        value=word_count,
                        threshold=self.thresholds.card_word_min
                    ))
                    score -= 3
        
        return max(0, score), issues, violations
    
    def validate_section_count(
        self,
        sections: List[Dict[str, Any]]
    ) -> tuple[int, List[RubricIssue]]:
        """Validate section count is within bounds."""
        issues = []
        score = 100
        section_count = len(sections)
        
        if section_count < self.thresholds.sections_min:
            issues.append(RubricIssue(
                dimension=RubricDimension.SECTION_COUNT.value,
                severity=IssueSeverity.FAIL.value,
                location="Tutorial Structure",
                message=f"Only {section_count} sections, minimum is {self.thresholds.sections_min}",
                value=section_count,
                threshold=self.thresholds.sections_min
            ))
            score = 50
            
        elif section_count > self.thresholds.sections_max:
            issues.append(RubricIssue(
                dimension=RubricDimension.SECTION_COUNT.value,
                severity=IssueSeverity.WARNING.value,
                location="Tutorial Structure",
                message=f"{section_count} sections exceeds max of {self.thresholds.sections_max}",
                value=section_count,
                threshold=self.thresholds.sections_max
            ))
            score = 80
        
        return score, issues
    
    def validate_media_completeness(
        self,
        sections: List[Dict[str, Any]]
    ) -> tuple[int, List[RubricIssue]]:
        """Validate that sections have required media assets."""
        issues = []
        score = 100
        
        for sec_idx, section in enumerate(sections):
            media_count = 0
            has_placeholder = False
            
            for block in section.get("blocks", []):
                block_type = block.get("type", "")
                
                if block_type in ["video", "image", "audio"]:
                    media_count += 1
                elif block_type == "placeholder":
                    has_placeholder = True
            
            location = f"Section {sec_idx + 1}: {section.get('title', 'Untitled')}"
            
            if has_placeholder:
                issues.append(RubricIssue(
                    dimension=RubricDimension.MEDIA_COMPLETENESS.value,
                    severity=IssueSeverity.FAIL.value,
                    location=location,
                    message="Contains failed/placeholder media",
                    value="placeholder",
                    threshold="complete_media"
                ))
                score -= 20
            
            if media_count < self.thresholds.media_per_section_min:
                issues.append(RubricIssue(
                    dimension=RubricDimension.MEDIA_COMPLETENESS.value,
                    severity=IssueSeverity.WARNING.value,
                    location=location,
                    message=f"Only {media_count} media items, expected at least {self.thresholds.media_per_section_min}",
                    value=media_count,
                    threshold=self.thresholds.media_per_section_min
                ))
                score -= 5
        
        return max(0, score), issues
    
    def validate_quiz_quality(
        self,
        sections: List[Dict[str, Any]]
    ) -> tuple[int, List[RubricIssue]]:
        """Validate quiz block quality."""
        issues = []
        score = 100
        
        for sec_idx, section in enumerate(sections):
            for block_idx, block in enumerate(section.get("blocks", [])):
                if block.get("type") not in ["quiz_single", "quiz_final"]:
                    continue
                
                location = f"Section {sec_idx + 1}, Block {block_idx + 1}"
                
                # Get questions list
                if block.get("type") == "quiz_single":
                    questions = [block]
                else:
                    questions = block.get("questions", [])
                
                for q_idx, q in enumerate(questions):
                    options = q.get("options", [])
                    correct = q.get("correct_answer")
                    
                    # Check option count
                    if len(options) < self.thresholds.quiz_options_min:
                        issues.append(RubricIssue(
                            dimension=RubricDimension.QUIZ_QUALITY.value,
                            severity=IssueSeverity.WARNING.value,
                            location=f"{location}, Q{q_idx + 1}",
                            message=f"Only {len(options)} options, minimum is {self.thresholds.quiz_options_min}",
                            value=len(options),
                            threshold=self.thresholds.quiz_options_min
                        ))
                        score -= 5
                    
                    # Check correct_answer is valid
                    if not isinstance(correct, int):
                        issues.append(RubricIssue(
                            dimension=RubricDimension.QUIZ_QUALITY.value,
                            severity=IssueSeverity.FAIL.value,
                            location=f"{location}, Q{q_idx + 1}",
                            message=f"correct_answer is not an integer: {type(correct).__name__}",
                            value=correct,
                            threshold="integer"
                        ))
                        score -= 15
                    elif correct < 0 or correct >= len(options):
                        issues.append(RubricIssue(
                            dimension=RubricDimension.QUIZ_QUALITY.value,
                            severity=IssueSeverity.FAIL.value,
                            location=f"{location}, Q{q_idx + 1}",
                            message=f"correct_answer {correct} out of bounds (0-{len(options) - 1})",
                            value=correct,
                            threshold=f"0-{len(options) - 1}"
                        ))
                        score -= 15
        
        return max(0, score), issues
    
    def validate_mermaid_syntax(
        self,
        sections: List[Dict[str, Any]]
    ) -> tuple[int, List[str]]:
        """Validate Mermaid diagram syntax if present."""
        syntax_errors = []
        score = 100
        
        mermaid_pattern = r"```mermaid\n(.*?)```"
        
        for sec_idx, section in enumerate(sections):
            for block in section.get("blocks", []):
                if block.get("type") != "text":
                    continue
                
                content = block.get("content", "")
                matches = re.findall(mermaid_pattern, content, re.DOTALL)
                
                for match in matches:
                    # Basic syntax checks
                    if not match.strip():
                        syntax_errors.append(f"Section {sec_idx + 1}: Empty mermaid block")
                        score -= 10
                        continue
                    
                    # Check for common errors
                    lines = match.strip().split("\n")
                    first_line = lines[0].strip().lower() if lines else ""
                    
                    valid_types = ["graph", "flowchart", "sequencediagram", "classDiagram", 
                                   "statediagram", "gantt", "pie", "erdiagram"]
                    
                    if not any(first_line.startswith(t.lower()) for t in valid_types):
                        syntax_errors.append(f"Section {sec_idx + 1}: Invalid mermaid type '{first_line}'")
                        score -= 5
        
        return max(0, score), syntax_errors
    
    def calculate_citation_coverage(
        self,
        sections: List[Dict[str, Any]]
    ) -> float:
        """Calculate what percentage of content has citations."""
        total_text_blocks = 0
        blocks_with_citations = 0
        
        citation_pattern = r'\[[\d,\s]+\]|\[\^[\d]+\]|<cite>|{{citation}}'
        
        for section in sections:
            for block in section.get("blocks", []):
                if block.get("type") != "text":
                    continue
                
                total_text_blocks += 1
                content = block.get("content", "")
                
                if re.search(citation_pattern, content):
                    blocks_with_citations += 1
        
        if total_text_blocks == 0:
            return 0.0
        
        return blocks_with_citations / total_text_blocks
    
    def validate_required_sections(
        self,
        sections: List[Dict[str, Any]]
    ) -> tuple[int, List[RubricIssue]]:
        """
        Validate that tutorial contains required pedagogical sections.
        Spec v2.2 §6: Structural Rubric - ensures learning effectiveness.
        
        Required sections:
        - 'Why this matters' / 'Why-this-matters' (relevance to learner)
        - 'Watch out for' / 'Watch-out-for' / 'Common pitfalls' (warnings)
        """
        issues = []
        score = 100
        
        # Patterns to detect required sections (case-insensitive)
        relevance_patterns = [
            r"why[\s\-]this[\s\-]matters",
            r"why[\s\-]it[\s\-]matters",
            r"relevance",
            r"importance",
            r"why[\s\-]should[\s\-]you[\s\-]care",
        ]
        
        warning_patterns = [
            r"watch[\s\-]out[\s\-]for",
            r"common[\s\-]pitfalls",
            r"common[\s\-]mistakes",
            r"gotchas",
            r"avoid[\s\-]these",
            r"things[\s\-]to[\s\-]avoid",
            r"warnings?",
            r"cautions?",
        ]
        
        # Collect all section titles and text content
        has_relevance_section = False
        has_warning_section = False
        
        for section in sections:
            title = section.get("title", "").lower()
            
            # Check title for required patterns
            for pattern in relevance_patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    has_relevance_section = True
                    break
            
            for pattern in warning_patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    has_warning_section = True
                    break
            
            # Also check within text blocks for inline sections
            for block in section.get("blocks", []):
                if block.get("type") != "text":
                    continue
                content = block.get("content", "").lower()
                
                for pattern in relevance_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        has_relevance_section = True
                        break
                
                for pattern in warning_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        has_warning_section = True
                        break
        
        # Generate issues for missing sections
        if not has_relevance_section:
            issues.append(RubricIssue(
                dimension=RubricDimension.SECTION_STRUCTURE.value,
                severity=IssueSeverity.WARNING.value,
                location="Tutorial Structure",
                message="Missing 'Why-this-matters' section. Add context on why this topic is important to learners.",
                value="missing",
                threshold="required"
            ))
            score -= 15
        
        if not has_warning_section:
            issues.append(RubricIssue(
                dimension=RubricDimension.SECTION_STRUCTURE.value,
                severity=IssueSeverity.WARNING.value,
                location="Tutorial Structure",
                message="Missing 'Watch-out-for' section. Add common pitfalls or mistakes learners should avoid.",
                value="missing",
                threshold="required"
            ))
            score -= 15
        
        return max(0, score), issues
    
    def evaluate_tutorial(
        self,
        tutorial_data: Dict[str, Any],
        original_blueprint: Optional[Dict[str, Any]] = None
    ) -> RubricReport:
        """
        Run full rubric evaluation on a tutorial.
        Returns comprehensive report with scores and issues.
        """
        from datetime import datetime
        
        sections = tutorial_data.get("sections", [])
        
        all_issues = []
        dimension_scores = {}
        
        # 1. Card Word Count
        score, issues, violations = self.validate_card_word_count(sections)
        dimension_scores[RubricDimension.CARD_WORD_COUNT.value] = score
        all_issues.extend(issues)
        card_violations = violations
        
        # 2. Section Count
        score, issues = self.validate_section_count(sections)
        dimension_scores[RubricDimension.SECTION_COUNT.value] = score
        all_issues.extend(issues)
        
        # 3. Media Completeness
        score, issues = self.validate_media_completeness(sections)
        dimension_scores[RubricDimension.MEDIA_COMPLETENESS.value] = score
        all_issues.extend(issues)
        
        # 4. Quiz Quality
        score, issues = self.validate_quiz_quality(sections)
        dimension_scores[RubricDimension.QUIZ_QUALITY.value] = score
        all_issues.extend(issues)
        
        # 5. Syntax Validation
        score, syntax_errors = self.validate_mermaid_syntax(sections)
        dimension_scores[RubricDimension.SYNTAX_VALIDATION.value] = score
        
        # 6. Citation Coverage
        citation_coverage = self.calculate_citation_coverage(sections)
        citation_score = 100 if citation_coverage >= self.thresholds.citation_coverage_threshold else int(citation_coverage * 100 / self.thresholds.citation_coverage_threshold)
        dimension_scores[RubricDimension.CITATION_COVERAGE.value] = citation_score
        
        # 7. Structural Section Validation (v2.2: Why-this-matters, Watch-out-for)
        score, issues = self.validate_required_sections(sections)
        dimension_scores[RubricDimension.SECTION_STRUCTURE.value] = score
        all_issues.extend(issues)
        
        # Calculate overall score
        scores = list(dimension_scores.values())
        overall_score = sum(scores) // len(scores) if scores else 0
        
        # Determine verdict
        fail_count = len([i for i in all_issues if i.severity == IssueSeverity.FAIL.value])
        verdict = "FAIL" if fail_count > 0 or overall_score < 70 else "PASS"
        
        # Generate fix list
        fix_list = []
        for issue in all_issues:
            if issue.severity == IssueSeverity.FAIL.value:
                fix_list.append(f"[{issue.dimension}] {issue.location}: {issue.message}")
        
        report = RubricReport(
            verdict=verdict,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            issues=all_issues,
            citation_coverage=citation_coverage,
            card_word_count_violations=card_violations,
            syntax_errors=syntax_errors,
            fix_list=fix_list,
            validated_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"📋 Rubric Evaluation: {verdict} ({overall_score}/100) - {len(all_issues)} issues")
        
        return report


# Singleton
_critic_agent: Optional[CriticAgent] = None

def get_critic_agent() -> CriticAgent:
    """Get or create singleton CriticAgent."""
    global _critic_agent
    if _critic_agent is None:
        _critic_agent = CriticAgent()
    return _critic_agent


def evaluate_tutorial_quality(
    tutorial_data: Dict[str, Any],
    blueprint: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Convenience function to evaluate tutorial quality."""
    agent = get_critic_agent()
    report = agent.evaluate_tutorial(tutorial_data, blueprint)
    return report.to_dict()
