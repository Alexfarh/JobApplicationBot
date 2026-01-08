'use client';

import { Briefcase, Calendar } from 'lucide-react';
import { Experience } from '@/hooks/use-profile';

interface ExperienceCardProps {
  experience: Experience;
}

export function ExperienceCard({ experience }: ExperienceCardProps) {
  return (
    <div className="border border-slate-700 rounded-lg p-6 bg-slate-900/50 hover:bg-slate-900 transition">
      {/* Header: Company and Title */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-lg font-semibold text-white">{experience.title}</h3>
          <p className="text-slate-400 flex items-center gap-2 mt-1">
            <Briefcase className="w-4 h-4" />
            {experience.company}
          </p>
        </div>
        {experience.duration_years && (
          <span className="px-3 py-1 bg-blue-500/20 text-blue-300 rounded-full text-sm font-medium">
            {experience.duration_years.toFixed(1)}y
          </span>
        )}
      </div>

      {/* Date Range */}
      {(experience.start_date || experience.end_date) && (
        <div className="flex items-center gap-2 text-slate-400 text-sm mb-4">
          <Calendar className="w-4 h-4" />
          <span>
            {experience.start_date} {experience.end_date && `– ${experience.end_date}`}
          </span>
        </div>
      )}

      {/* Description */}
      {experience.description && (
        <div className="text-slate-300 text-sm leading-relaxed">
          {experience.description.split('\n').map((line, i) => (
            <p key={i} className={line.startsWith('•') ? 'ml-4' : ''}>
              {line}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
