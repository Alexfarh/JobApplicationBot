'use client';

import { useEffect, useState } from 'react';

export interface Experience {
  company: string;
  title: string;
  start_date?: string;
  end_date?: string;
  duration_years?: number;
  description?: string;
}

export interface Education {
  institution: string;
  degree: string;
  field?: string;
  graduation_year?: string;
}

export interface ResumeData {
  name?: string;
  email?: string;
  phone?: string;
  github?: string;
  linkedin?: string;
  portfolio?: string;
  skills: string[];
  experience: Experience[];
  education: Education[];
  projects: string[];
  total_experience_years?: number;
  seniority_level?: string;
}

export interface UserProfile {
  user_id: string;
  email: string;
  role: string;
  full_name?: string;
  phone?: string;
  address_street?: string;
  address_city?: string;
  address_state?: string;
  address_zip?: string;
  address_country?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  target_companies?: string[];
  expected_salary_hourly_min?: number;
  expected_salary_annual_min?: number;
  expected_salary_currency?: string;
  salary_flexibility_note?: string;
  resume_uploaded: boolean;
  resume_filename?: string;
  resume_uploaded_at?: string;
  resume_size_bytes?: number;
  resume_data?: ResumeData;
  internship_only: boolean;
  preferred_job_types: string[];
  mandatory_questions?: Record<string, string>;
  preferences?: Record<string, unknown>;
  profile_complete: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export function useProfile() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/profile', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch profile: ${response.statusText}`);
      }

      const data: UserProfile = await response.json();
      setProfile(data);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(message);
      console.error('Error fetching profile:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  return { profile, loading, error, refetch: fetchProfile };
}
