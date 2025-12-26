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
import { Loader2, Upload, FileText, Trash2 } from "lucide-react"

export default function ProfilePage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const isOnboarding = searchParams.get("onboarding") === "true"

  const [profile, setProfile] = useState<ProfileResponse | null>(null)
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
      setProfile(data)

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

  if (isLoading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-gray-500" />
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-neutral-900 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          {isOnboarding && (
            <Alert className="mb-6">
              <AlertDescription>
                👋 Welcome! Please complete your profile to start automating job applications.
              </AlertDescription>
            </Alert>
          )}
          <Button
            variant="ghost"
            className="mb-6 bg-black text-white border border-white hover:bg-black hover:text-white hover:border-blue-400 focus-visible:ring-2 focus-visible:ring-blue-400 transition-all duration-150 hover:scale-105 active:scale-95 shadow-lg outline-none"
            onClick={() => router.push('/')}
            >
            ← Back to Dashboard
          </Button>
          <Card>
            <CardHeader>
              <CardTitle>Your Profile</CardTitle>
              <CardDescription>
                Manage your personal information, resume, and automation preferences
              </CardDescription>
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
