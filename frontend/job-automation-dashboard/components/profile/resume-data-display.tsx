'use client';

import { ResumeData } from '@/hooks/use-profile';
import { SkillsBadges } from './skills-badges';
import { ExperienceCard } from './experience-card';
import { GraduationCap, Lightbulb } from 'lucide-react';

interface ResumeDataDisplayProps {
  resume: ResumeData;
}

export function ResumeDataDisplay({ resume }: ResumeDataDisplayProps) {
  return (
    <div className="space-y-8">
      {/* Skills Section */}
      {resume.skills && resume.skills.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            💻 Skills
          </h2>
          <SkillsBadges skills={resume.skills} />
        </section>
      )}

      {/* Experience Section */}
      {resume.experience && resume.experience.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            💼 Experience
          </h2>
          <div className="space-y-4">
            {resume.experience.map((exp, idx) => (
              <ExperienceCard key={idx} experience={exp} />
            ))}
          </div>
        </section>
      )}

      {/* Education Section */}
      {resume.education && resume.education.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <GraduationCap className="w-6 h-6" />
            Education
          </h2>
          <div className="space-y-4">
            {resume.education.map((edu, idx) => (
              <div
                key={idx}
                className="border border-slate-700 rounded-lg p-6 bg-slate-900/50 hover:bg-slate-900 transition"
              >
                <h3 className="text-lg font-semibold text-white">{edu.degree}</h3>
                <p className="text-slate-400 mt-1">{edu.institution}</p>
                {edu.field && <p className="text-slate-400 text-sm mt-1">Focus: {edu.field}</p>}
                {edu.graduation_year && (
                  <p className="text-slate-500 text-sm mt-2">Graduation: {edu.graduation_year}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Projects Section */}
      {resume.projects && resume.projects.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold text-white mb-4 flex items-center gap-2">
            <Lightbulb className="w-6 h-6" />
            Projects
          </h2>
          <div className="space-y-3">
            {resume.projects.map((project, idx) => (
              <div
                key={idx}
                className="border border-slate-700 rounded-lg p-4 bg-slate-900/50 hover:bg-slate-900 transition"
              >
                <p className="text-slate-300">{project}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
