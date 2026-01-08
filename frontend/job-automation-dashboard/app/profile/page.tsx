"use client"

import { useState, useEffect } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { profileAPI, type ProfileResponse, type MandatoryQuestions } from "@/lib/auth"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { ProtectedRoute } from "@/components/protected-route"
import { Loader2, Upload, FileText, Trash2, Edit2 } from "lucide-react"
import { ProfileHeader } from "@/components/profile/profile-header"
import { ResumeDataDisplay } from "@/components/profile/resume-data-display"
import { useProfile } from "@/hooks/use-profile"

export default function ProfilePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const isOnboarding = searchParams.get("onboarding") === "true"

  // Use the new hook
  const { profile, loading, error: hookError } = useProfile()
  
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  // Form state
  const [fullName, setFullName] = useState("")
  const [phone, setPhone] = useState("")
  const [addressCity, setAddressCity] = useState("")
  const [addressState, setAddressState] = useState("")
  const [addressCountry, setAddressCountry] = useState("Canada")
  const [linkedinUrl, setLinkedinUrl] = useState("")
  const [githubUrl, setGithubUrl] = useState("")
  const [portfolioUrl, setPortfolioUrl] = useState("")

  // Questions state
  const [workAuth, setWorkAuth] = useState("")
  const [veteranStatus, setVeteranStatus] = useState("")
  const [disabilityStatus, setDisabilityStatus] = useState("")

  // Preferences state
  const [optimisticMode, setOptimisticMode] = useState(true)
  const [requireApproval, setRequireApproval] = useState(true)

  // Resume state
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [isUploadingResume, setIsUploadingResume] = useState(false)

  useEffect(() => {
    loadProfile()
  }, [])

  const loadProfile = async () => {
    try {
      const data = await profileAPI.get()

      // Populate form
      setFullName(data.full_name || "")
      setPhone(data.phone || "")
      setAddressCity(data.address_city || "")
      setAddressState(data.address_state || "")
      setAddressCountry(data.address_country || "Canada")
      setLinkedinUrl(data.linkedin_url || "")
      setGithubUrl(data.github_url || "")
      setPortfolioUrl(data.portfolio_url || "")

      if (data.mandatory_questions) {
        setWorkAuth(data.mandatory_questions.work_authorization || "")
        setVeteranStatus(data.mandatory_questions.veteran_status || "")
        setDisabilityStatus(data.mandatory_questions.disability_status || "")
      }

      setOptimisticMode(data.preferences.optimistic_mode)
      setRequireApproval(data.preferences.require_approval)

      setIsLoading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile")
      setIsLoading(false)
    }
  }

  const handleSavePersonalInfo = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setError("")
    setSuccess("")

    try {
      const data = await profileAPI.update({
        full_name: fullName,
        phone: phone,
        address_city: addressCity,
        address_state: addressState,
        address_country: addressCountry,
        linkedin_url: linkedinUrl || undefined,
        github_url: githubUrl || undefined,
        portfolio_url: portfolioUrl || undefined,
      })
      setProfile(data)
      setSuccess("Personal information saved!")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveQuestions = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setError("")
    setSuccess("")

    try {
      const questions: MandatoryQuestions = {
        work_authorization: workAuth,
        veteran_status: veteranStatus,
        disability_status: disabilityStatus,
      }
      const data = await profileAPI.updateQuestions(questions)
      setProfile(data)
      setSuccess("Mandatory questions saved!")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setIsSaving(false)
    }
  }

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setError("")
    setSuccess("")

    try {
      const data = await profileAPI.updatePreferences({
        optimistic_mode: optimisticMode,
        require_approval: requireApproval,
      })
      setProfile(data)
      setSuccess("Preferences saved!")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setIsSaving(false)
    }
  }

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploadingResume(true)
    setError("")
    setSuccess("")

    try {
      const data = await profileAPI.uploadResume(file)
      setProfile(data)
      setSuccess("Resume uploaded successfully!")
      setResumeFile(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload resume")
    } finally {
      setIsUploadingResume(false)
    }
  }

  const handleResumeDelete = async () => {
    if (!confirm("Are you sure you want to delete your resume?")) return

    try {
      const data = await profileAPI.deleteResume()
      setProfile(data)
      setSuccess("Resume deleted")
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

          <Button
            variant="ghost"
            className="mb-6 bg-slate-900 text-white border border-slate-700 hover:bg-slate-800 hover:border-blue-400"
            onClick={() => router.push('/')}
          >
            ← Back to Dashboard
          </Button>

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
                  <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-8 text-center">
                    <FileText className="w-12 h-12 text-slate-500 mx-auto mb-4" />
                    <p className="text-slate-400">No resume uploaded yet</p>
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

          {/* EDIT MODE SECTION */}
          <Card className="bg-slate-900/50 border-slate-700">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Edit2 className="w-5 h-5" />
                    Edit Profile
                  </CardTitle>
                  <CardDescription>Update your personal information and settings</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {success && (
                <Alert className="mb-4">
                  <AlertDescription>{success}</AlertDescription>
                </Alert>
              )}

              <Tabs defaultValue="personal">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="personal">Personal</TabsTrigger>
                  <TabsTrigger value="resume">Resume</TabsTrigger>
                  <TabsTrigger value="questions">Questions</TabsTrigger>
                  <TabsTrigger value="preferences">Preferences</TabsTrigger>
                </TabsList>

                <TabsContent value="personal" className="space-y-4">
                  <form onSubmit={handleSavePersonalInfo} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="fullName">Full Name *</Label>
                        <Input
                          id="fullName"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="phone">Phone Number *</Label>
                        <Input
                          id="phone"
                          type="tel"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          required
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="city">City</Label>
                        <Input
                          id="city"
                          value={addressCity}
                          onChange={(e) => setAddressCity(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="state">State</Label>
                        <Input
                          id="state"
                          value={addressState}
                          onChange={(e) => setAddressState(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="country">Country</Label>
                        <Input
                          id="country"
                          value={addressCountry}
                          onChange={(e) => setAddressCountry(e.target.value)}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="linkedin">LinkedIn URL</Label>
                      <Input
                        id="linkedin"
                        type="url"
                        placeholder="https://linkedin.com/in/username"
                        value={linkedinUrl}
                        onChange={(e) => setLinkedinUrl(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="github">GitHub URL</Label>
                      <Input
                        id="github"
                        type="url"
                        placeholder="https://github.com/username"
                        value={githubUrl}
                        onChange={(e) => setGithubUrl(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="portfolio">Portfolio URL</Label>
                      <Input
                        id="portfolio"
                        type="url"
                        placeholder="https://yourportfolio.com"
                        value={portfolioUrl}
                        onChange={(e) => setPortfolioUrl(e.target.value)}
                      />
                    </div>

                    <Button type="submit" disabled={isSaving}>
                      {isSaving ? "Saving..." : "Save Personal Info"}
                    </Button>
                  </form>
                </TabsContent>

                <TabsContent value="resume" className="space-y-4">
                  {profile?.resume_uploaded ? (
                    <div className="border rounded-lg p-4 space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <FileText className="h-8 w-8 text-gray-500" />
                          <div>
                            <p className="font-medium">{profile.resume_filename}</p>
                            <p className="text-sm text-gray-500">
                              Uploaded {new Date(profile.resume_uploaded_at!).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex space-x-2">
                          <Button variant="outline" size="sm" onClick={handleDownloadResume}>
                            Download
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={handleResumeDelete}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="border-2 border-dashed rounded-lg p-8 text-center">
                      <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                      <Label htmlFor="resume-upload" className="cursor-pointer">
                        <span className="text-blue-600 hover:text-blue-700">
                          Click to upload resume
                        </span>
                        <span className="text-gray-500"> or drag and drop</span>
                      </Label>
                      <p className="text-sm text-gray-500 mt-2">PDF or DOCX, max 5MB</p>
                      <Input
                        id="resume-upload"
                        type="file"
                        accept=".pdf,.doc,.docx"
                        className="hidden"
                        onChange={handleResumeUpload}
                        disabled={isUploadingResume}
                      />
                      {isUploadingResume && <Loader2 className="h-6 w-6 animate-spin mx-auto mt-4" />}
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="questions" className="space-y-4">
                  <form onSubmit={handleSaveQuestions} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="workAuth">Work Authorization *</Label>
                      <Select value={workAuth} onValueChange={setWorkAuth} required>
                        <SelectTrigger>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="yes">Authorized to work in US</SelectItem>
                          <SelectItem value="no">Require sponsorship</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="veteran">Veteran Status *</Label>
                      <Select value={veteranStatus} onValueChange={setVeteranStatus} required>
                        <SelectTrigger>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="no">Not a veteran</SelectItem>
                          <SelectItem value="yes">Veteran</SelectItem>
                          <SelectItem value="decline">Prefer not to answer</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="disability">Disability Status *</Label>
                      <Select
                        value={disabilityStatus}
                        onValueChange={setDisabilityStatus}
                        required
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select..." />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="no">No disability</SelectItem>
                          <SelectItem value="yes">Have a disability</SelectItem>
                          <SelectItem value="decline">Prefer not to answer</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <Button type="submit" disabled={isSaving}>
                      {isSaving ? "Saving..." : "Save Questions"}
                    </Button>
                  </form>
                </TabsContent>

                <TabsContent value="preferences" className="space-y-4">
                  <form onSubmit={handleSavePreferences} className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Optimistic Mode</Label>
                        <p className="text-sm text-gray-500">
                          Answer experience questions optimistically when you have related skills
                        </p>
                      </div>
                      <Switch
                        checked={optimisticMode}
                        onCheckedChange={setOptimisticMode}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <Label>Require Approval</Label>
                        <p className="text-sm text-gray-500">
                          Review applications before final submission
                        </p>
                      </div>
                      <Switch
                        checked={requireApproval}
                        onCheckedChange={setRequireApproval}
                      />
                    </div>

                    <Button type="submit" disabled={isSaving}>
                      {isSaving ? "Saving..." : "Save Preferences"}
                    </Button>
                  </form>
                </TabsContent>
              </Tabs>

              {isOnboarding && profile?.profile_complete && (
                <div className="mt-6 pt-6 border-t">
                  <Button onClick={handleContinue} className="w-full">
                    Continue to Dashboard →
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}
