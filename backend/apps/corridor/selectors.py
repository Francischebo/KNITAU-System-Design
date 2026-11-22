from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from .models import DiasporaMentor

_SYNONYMS: dict[str, set[str]] = {
    "renewable": {"solar", "clean", "green", "pv", "energy"},
    "solar": {"renewable", "pv", "energy", "grid"},
    "python": {"django", "backend", "api", "data"},
    "react": {"frontend", "typescript", "javascript", "ui"},
    "nursing": {"clinical", "healthcare", "patient", "care"},
    "accounting": {"finance", "audit", "bookkeeping", "tax"},
}


@dataclass(frozen=True)
class RankedMentor:
    mentor: DiasporaMentor
    similarity_score: int
    similarity_label: str
    matched_tags: list[str]
    matched_skills: list[str]


def _tokenize(label: str) -> set[str]:
    tokens = {tok for tok in re.split(r"[^a-z0-9]+", label.lower()) if len(tok) >= 2}
    expanded = set(tokens)
    for tok in tokens:
        expanded.update(_SYNONYMS.get(tok, set()))
    return expanded


def calculate_tag_skill_similarity(
    expertise_tags: Iterable[str],
    active_skills: Iterable[str],
    is_verified: bool,
) -> tuple[int, str, list[str], list[str]]:
    clean_tags = [t.strip() for t in expertise_tags if t and t.strip()]
    clean_skills = [s.strip() for s in active_skills if s and s.strip()]

    if not clean_tags or not clean_skills:
        base = 20 if is_verified else 10
        return base, "General Mentor", [], []

    tag_tokens = [(tag, _tokenize(tag)) for tag in clean_tags]
    skill_tokens = [(skill, _tokenize(skill)) for skill in clean_skills]

    matched_tags: list[str] = []
    matched_skills: list[str] = []
    best_pair_scores: list[float] = []

    for skill, s_toks in skill_tokens:
        best_for_skill = 0.0
        for tag, t_toks in tag_tokens:
            union = s_toks | t_toks
            if not union:
                continue
            overlap = len(s_toks & t_toks) / len(union)
            if overlap > 0 and tag not in matched_tags:
                matched_tags.append(tag)
            if overlap > best_for_skill:
                best_for_skill = overlap
        if best_for_skill > 0:
            matched_skills.append(skill)
        best_pair_scores.append(best_for_skill)

    passport_coverage = len(matched_skills) / len(clean_skills)
    tag_precision = len(matched_tags) / len(clean_tags)
    mean_pair = sum(best_pair_scores) / len(best_pair_scores)

    raw_score = (0.45 * passport_coverage + 0.30 * mean_pair + 0.25 * tag_precision) * 100
    if is_verified:
        raw_score += 5
    score = max(0, min(99, round(raw_score)))

    if score >= 65:
        label = "Strong Match"
    elif score >= 35:
        label = "Partial Match"
    else:
        label = "General Mentor"

    return score, label, matched_tags, matched_skills


def rank_mentors_for_passport_skills(
    *, active_skills: list[str], verified_only: bool = True
) -> list[RankedMentor]:
    qs = DiasporaMentor.objects.active()
    if verified_only:
        qs = qs.filter(is_verified=True)

    ranked: list[RankedMentor] = []
    for mentor in qs:
        score, label, m_tags, m_skills = calculate_tag_skill_similarity(
            mentor.expertise_tags, active_skills, mentor.is_verified
        )
        ranked.append(
            RankedMentor(
                mentor=mentor,
                similarity_score=score,
                similarity_label=label,
                matched_tags=m_tags,
                matched_skills=m_skills,
            )
        )

    ranked.sort(key=lambda item: (-item.similarity_score, item.mentor.full_name))
    return ranked
