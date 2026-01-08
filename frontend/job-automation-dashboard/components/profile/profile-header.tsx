'use client';

import { Mail, Phone, Github, Linkedin, Globe } from 'lucide-react';
import { UserProfile } from '@/hooks/use-profile';

interface ProfileHeaderProps {
  profile: UserProfile;
}

export function ProfileHeader({ profile }: ProfileHeaderProps) {
  return (
    <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-lg p-8 mb-8">
      {/* Name and Title */}
      <div className="mb-6">
        <h1 className="text-4xl font-bold mb-2">{profile.full_name || 'User'}</h1>
        {profile.resume_data?.seniority_level && (
          <p className="text-lg text-slate-300">
            {profile.resume_data.seniority_level.charAt(0).toUpperCase() +
              profile.resume_data.seniority_level.slice(1)}{' '}
            Level
            {profile.resume_data.total_experience_years && (
              <> • {profile.resume_data.total_experience_years.toFixed(1)} years experience</>
            )}
          </p>
        )}
      </div>

      {/* Contact Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Email */}
        {profile.email && (
          <div className="flex items-center gap-3">
            <Mail className="w-5 h-5 text-blue-400" />
            <span className="text-slate-200">{profile.email}</span>
          </div>
        )}

        {/* Phone */}
        {profile.phone && (
          <div className="flex items-center gap-3">
            <Phone className="w-5 h-5 text-green-400" />
            <span className="text-slate-200">{profile.phone}</span>
          </div>
        )}

        {/* GitHub */}
        {profile.github_url && (
          <a
            href={profile.github_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 hover:opacity-80 transition"
          >
            <Github className="w-5 h-5 text-purple-400" />
            <span className="text-slate-200">{profile.github_url}</span>
          </a>
        )}

        {/* LinkedIn */}
        {profile.linkedin_url && (
          <a
            href={profile.linkedin_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 hover:opacity-80 transition"
          >
            <Linkedin className="w-5 h-5 text-blue-500" />
            <span className="text-slate-200">{profile.linkedin_url}</span>
          </a>
        )}

        {/* Portfolio */}
        {profile.portfolio_url && (
          <a
            href={profile.portfolio_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 hover:opacity-80 transition"
          >
            <Globe className="w-5 h-5 text-orange-400" />
            <span className="text-slate-200">{profile.portfolio_url}</span>
          </a>
        )}
      </div>

      {/* Location */}
      {profile.address_city && (
        <div className="mt-4 text-slate-300">
          📍 {profile.address_city}
          {profile.address_state && `, ${profile.address_state}`}
          {profile.address_country && `, ${profile.address_country}`}
        </div>
      )}
    </div>
  );
}
