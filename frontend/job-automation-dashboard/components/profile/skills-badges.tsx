'use client';

interface SkillsBadgesProps {
  skills: string[];
}

export function SkillsBadges({ skills }: SkillsBadgesProps) {
  if (!skills || skills.length === 0) {
    return null;
  }

  // Color mapping for different skill types
  const getSkillColor = (skill: string) => {
    const lower = skill.toLowerCase();
    
    if (['python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'go', 'rust'].some(l => lower.includes(l))) {
      return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
    }
    if (['react', 'vue', 'angular', 'next.js', 'svelte'].some(l => lower.includes(l))) {
      return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
    }
    if (['aws', 'docker', 'kubernetes', 'terraform', 'jenkins'].some(l => lower.includes(l))) {
      return 'bg-orange-500/20 text-orange-300 border-orange-500/30';
    }
    if (['postgresql', 'mongodb', 'redis', 'sql', 'firebase'].some(l => lower.includes(l))) {
      return 'bg-green-500/20 text-green-300 border-green-500/30';
    }
    if (['machine learning', 'ai', 'nlp', 'pytorch', 'tensorflow'].some(l => lower.includes(l))) {
      return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
    }
    
    return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
  };

  return (
    <div className="flex flex-wrap gap-2">
      {skills.map((skill) => (
        <span
          key={skill}
          className={`px-3 py-1 rounded-full text-sm font-medium border ${getSkillColor(skill)}`}
        >
          {skill}
        </span>
      ))}
    </div>
  );
}
