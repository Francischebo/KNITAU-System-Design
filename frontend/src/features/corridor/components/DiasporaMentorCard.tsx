import React from 'react';
import { SIMILARITY_BADGE_TOKENS } from '../../../design-system/tokens';
import type { DiasporaMentorMatch } from '../types';

interface Props {
  mentor: DiasporaMentorMatch;
  onRequestMentorship: (mentorId: string) => void;
}

export const DiasporaMentorCard: React.FC<Props> = ({ mentor, onRequestMentorship }) => {
  const badgeStyle = SIMILARITY_BADGE_TOKENS[mentor.similarity_label];

  return (
    <article className="rounded-lg border border-[#231F20]/15 bg-[#FFFFFF] p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-bold text-[#231F20]">{mentor.full_name}</h3>
          <p className="text-xs text-[#231F20]/75">
            {mentor.role_title} • {mentor.country}
          </p>
        </div>
        <span
          className="rounded px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
          style={{ backgroundColor: badgeStyle.bg, color: badgeStyle.text }}
        >
          {mentor.similarity_score}% {mentor.similarity_label}
        </span>
      </div>

      <p className="mt-3 text-sm leading-relaxed text-[#231F20]/85">{mentor.bio}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {mentor.expertise_tags.map((tag) => {
          const isMatched = mentor.matched_tags.includes(tag);
          return (
            <span
              key={tag}
              className={`rounded border px-2 py-0.5 text-xs ${
                isMatched
                  ? 'border-[#0F6B38] bg-[#0F6B38]/10 font-semibold text-[#0F6B38]'
                  : 'border-[#231F20]/20 text-[#231F20]/80'
              }`}
            >
              {tag}
            </span>
          );
        })}
      </div>

      <div className="mt-4 flex justify-end">
        <button
          type="button"
          onClick={() => onRequestMentorship(mentor.id)}
          className="rounded bg-[#231F20] px-4 py-2 text-xs font-semibold text-[#FFFFFF] hover:bg-[#0F6B38]"
        >
          Request Mentorship
        </button>
      </div>
    </article>
  );
};
