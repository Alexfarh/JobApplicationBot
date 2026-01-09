"use client"

import { useState, useEffect, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { profileAPI, type ProfileResponse } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ProtectedRoute } from "@/components/protected-route"
import { Loader2, Upload, FileText, Trash2 } from "lucide-react"
import { ProfileHeader } from "@/components/profile/profile-header"
import { ResumeDataDisplay } from "@/components/profile/resume-data-display"
import { useProfile } from "@/hooks/use-profile"

function ProfilePageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const isOnboarding = searchParams.get("onboarding") === "true"

  // Use the new hook
  const { profile, loading, error: hookError } = useProfile()
  
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")

  // Resume state
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [isUploadingResume, setIsUploadingResume] = useState(false)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      await profileAPI.get()
      setIsLoading(false)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load profile"
      // Set default values for new profile
      setIsLoading(false)
    }
  }

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploadingResume(true)
    setError("")

    try {
      await profileAPI.uploadResume(file)
      setResumeFile(null)
      // Reload to get fresh data from hook
      await loadProfile()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload resume")
    } finally {
      setIsUploadingResume(false)
    }
  }

  const handleResumeDelete = async () => {
    if (!confirm("Are you sure you want to delete your resume?")) return

    try {
      await profileAPI.deleteResume()
      // Reload to get fresh data from hook
      await loadProfile()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete resume")
    }
  }

  const handleDownloadResume = async () => {
    try {
      const blob = await profileAPI.downloadResume()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = profile?.resume_filename || "resume.pdf"
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download resume")
    }
  }

  const handleContinue = () => {
    router.push("/dashboard")
  }

  if (isLoading || loading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-neutral-900 flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        </div>
      </ProtectedRoute>
    )
  }

  if (hookError) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-neutral-900 py-8 px-4">
          <div className="max-w-5xl mx-auto">
            <Alert variant="destructive">
              <AlertDescription>{hookError}</AlertDescription>
            </Alert>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  if (!profile) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-neutral-900 py-8 px-4">
          <div className="max-w-5xl mx-auto">
            <p className="text-slate-400">No profile found</p>
          </div>
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-950 py-8 px-4">
        <div className="max-w-5xl mx-auto">
          {isOnboarding && (
            <Alert className="mb-6 bg-blue-500/10 border-blue-500/20">
              <AlertDescription className="text-blue-200">
                👋 Welcome! Here's your profile with extracted resume data.
              </AlertDescription>
            </Alert>
          )}

          <div className="mb-6 flex items-center justify-between">
            <Button
              variant="ghost"
              className="bg-slate-900 text-white border border-slate-700 hover:bg-slate-800 hover:border-blue-400"
              onClick={() => router.push('/')}
            >
              ← Back to Dashboard
            </Button>
            <Button
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => router.push('/profile/edit')}
            >
              Edit Profile
            </Button>
          </div>

          {/* PROFILE VIEW SECTION */}
          <div className="mb-12">
            {/* Profile Header with Resume Data */}
            {profile && <ProfileHeader profile={profile} />}

            {/* Resume Data Display */}
            <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Left Column: Resume Data */}
              <div className="lg:col-span-2">
                {profile.resume_data ? (
                  <ResumeDataDisplay resume={profile.resume_data} />
                ) : (
                  <div className="bg-slate-900/50 border border-slate-700 border-dashed rounded-lg p-8 text-center hover:bg-slate-900/70 hover:border-slate-600 transition cursor-pointer group"
                    onClick={() => document.getElementById('resume-upload-input')?.click()}>
                    <FileText className="w-12 h-12 text-slate-500 mx-auto mb-4 group-hover:text-slate-400 transition" />
                    <p className="text-slate-400 group-hover:text-slate-300 transition font-medium">Click to upload resume</p>
                    <p className="text-xs text-slate-500 mt-2">PDF or DOCX (Max 5MB)</p>
                    <input
                      id="resume-upload-input"
                      type="file"
                      accept=".pdf,.docx"
                      onChange={handleResumeUpload}
                      disabled={isUploadingResume}
                      className="hidden"
                    />
                  </div>
                )}
              </div>

              {/* Right Column: Status and Preferences */}
              <div className="space-y-6">
                {/* Resume Status */}
                <Card className="bg-slate-900/50 border-slate-700">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Resume Status</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {profile.resume_uploaded ? (
                      <>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                          <p className="text-sm text-green-300 font-medium">Uploaded</p>
                        </div>
                        {profile.resume_filename && (
                          <p className="text-xs text-slate-400">{profile.resume_filename}</p>
                        )}
                        {profile.resume_size_bytes && (
                          <p className="text-xs text-slate-500">
                            {(profile.resume_size_bytes / 1024).toFixed(1)} KB
                          </p>
                        )}
                      </>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-slate-500 rounded-full"></span>
                        <p className="text-sm text-slate-400">Not uploaded</p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Job Preferences */}
                <Card className="bg-slate-900/50 border-slate-700">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Job Preferences</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <p className="text-xs text-slate-400 mb-1">Internship Only</p>
                      <p className="text-sm font-medium text-white">
                        {profile.internship_only ? '✓ Yes' : 'No'}
                      </p>
                    </div>
                    {profile.preferred_job_types && profile.preferred_job_types.length > 0 && (
                      <div>
                        <p className="text-xs text-slate-400 mb-2">Preferred Roles</p>
                        <div className="flex flex-wrap gap-2">
                          {profile.preferred_job_types.slice(0, 4).map((type) => (
                            <span
                              key={type}
                              className="px-2 py-1 bg-blue-500/20 text-blue-300 rounded text-xs"
                            >
                              {type}
                            </span>
                          ))}
                          {profile.preferred_job_types.length > 4 && (
                            <span className="px-2 py-1 text-slate-400 text-xs">
                              +{profile.preferred_job_types.length - 4} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>

          {isOnboarding && profile?.profile_complete && (
            <div className="mt-8 text-center">
              <Button onClick={handleContinue} className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2">
                Continue to Dashboard →
              </Button>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  )
}

export default function ProfilePage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><Loader2 className="h-8 w-8 animate-spin" /></div>}>
      <ProfilePageContent />
    </Suspense>
  )
}
