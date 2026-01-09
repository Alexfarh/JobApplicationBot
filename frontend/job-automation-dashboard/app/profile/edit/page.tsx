"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { profileAPI, type ProfileResponse, type MandatoryQuestions } from "@/lib/auth"
import { JOB_TYPES, COMPANIES } from "@/lib/job-preferences"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { ProtectedRoute } from "@/components/protected-route"
import { Loader2, X } from "lucide-react"
import { useProfile } from "@/hooks/use-profile"
import { MultiSelect } from "@/components/multi-select"

export default function EditProfilePage() {
  const router = useRouter()
  const { profile, loading: profileLoading, refetch } = useProfile()

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

  // Job preferences state
  const [preferredJobTypes, setPreferredJobTypes] = useState<string[]>([])
  const [internshipOnly, setInternshipOnly] = useState(false)
  const [targetCompanies, setTargetCompanies] = useState<string[]>([])

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

      setOptimisticMode(data.preferences?.optimistic_mode ?? true)
      setRequireApproval(data.preferences?.require_approval ?? true)

      // Job preferences
      setPreferredJobTypes(data.preferred_job_types || [])
      setInternshipOnly(data.internship_only ?? false)
      setTargetCompanies(data.target_companies || [])

      setIsLoading(false)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load profile"
      // Set default values for new profile
      setAddressCountry("Canada")
      setOptimisticMode(true)
      setRequireApproval(true)
      setError("")
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
      setSuccess("Personal information saved!")
      // Reload to get fresh data from hook
      await loadProfile()
      await refetch()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setIsSaving(false)
    }
  }

  const handleAutofillFromResume = () => {
    if (!profile?.resume_data) {
      setError("No resume data available to autofill")
      return
    }

    const resume = profile.resume_data

    // Autofill name and contact info from resume
    if (resume.name && !fullName) {
      setFullName(resume.name)
    }
    if (resume.phone && !phone) {
      setPhone(resume.phone)
    }
    if (resume.linkedin && !linkedinUrl) {
      setLinkedinUrl(resume.linkedin)
    }
    if (resume.github && !githubUrl) {
      setGithubUrl(resume.github)
    }
    if (resume.portfolio && !portfolioUrl) {
      setPortfolioUrl(resume.portfolio)
    }

    setSuccess("Profile autofilled from resume! Review and save the changes.")
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
      setSuccess("Mandatory questions saved!")
      // Reload to get fresh data
      await loadProfile()
      await refetch()
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
      setSuccess("Preferences saved!")
      // Reload to get fresh data
      await loadProfile()
      await refetch()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveJobPreferences = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    setError("")
    setSuccess("")

    try {
      const data = await profileAPI.update({
        preferred_job_types: preferredJobTypes,
        internship_only: internshipOnly,
        target_companies: targetCompanies,
      })
      setSuccess("Job preferences saved!")
      // Reload to get fresh data
      await loadProfile()
      await refetch()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save")
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <ProtectedRoute>
        <div className="min-h-screen bg-slate-950 py-8 px-4 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
        </div>
      </ProtectedRoute>
    )
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-950 py-8 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6 flex items-center justify-between">
            <h1 className="text-3xl font-bold text-white">Edit Profile</h1>
            <Button
              variant="ghost"
              className="text-slate-400 hover:text-white"
              onClick={() => router.back()}
            >
              <X className="w-5 h-5" />
            </Button>
          </div>

          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert className="mb-4 bg-green-500/10 border-green-500/20">
              <AlertDescription className="text-green-300">{success}</AlertDescription>
            </Alert>
          )}

          <Card className="bg-slate-900/50 border-slate-700">
            <CardHeader>
              <CardTitle>Update Your Information</CardTitle>
              <CardDescription>Manage your profile, preferences, and job search settings</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="personal" className="w-full">
                <TabsList className="grid w-full grid-cols-4 mb-6">
                  <TabsTrigger value="personal">Personal</TabsTrigger>
                  <TabsTrigger value="questions">Questions</TabsTrigger>
                  <TabsTrigger value="preferences">Automation</TabsTrigger>
                  <TabsTrigger value="jobs">Job Search</TabsTrigger>
                </TabsList>

                {/* Personal Info Tab */}
                <TabsContent value="personal" className="space-y-4">
                  {profile?.resume_data && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={handleAutofillFromResume}
                      className="w-full bg-slate-800 border-slate-600 hover:bg-slate-700 text-white"
                    >
                      ⚡ Autofill from Resume
                    </Button>
                  )}
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

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="city">City</Label>
                        <Input
                          id="city"
                          value={addressCity}
                          onChange={(e) => setAddressCity(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="state">State/Province</Label>
                        <Input
                          id="state"
                          value={addressState}
                          onChange={(e) => setAddressState(e.target.value)}
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="country">Country</Label>
                      <Input
                        id="country"
                        value={addressCountry}
                        onChange={(e) => setAddressCountry(e.target.value)}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="linkedin">LinkedIn URL</Label>
                      <Input
                        id="linkedin"
                        type="url"
                        value={linkedinUrl}
                        onChange={(e) => setLinkedinUrl(e.target.value)}
                        placeholder="https://linkedin.com/in/..."
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="github">GitHub URL</Label>
                      <Input
                        id="github"
                        type="url"
                        value={githubUrl}
                        onChange={(e) => setGithubUrl(e.target.value)}
                        placeholder="https://github.com/..."
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="portfolio">Portfolio URL</Label>
                      <Input
                        id="portfolio"
                        type="url"
                        value={portfolioUrl}
                        onChange={(e) => setPortfolioUrl(e.target.value)}
                        placeholder="https://..."
                      />
                    </div>

                    <Button
                      type="submit"
                      disabled={isSaving}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Save Personal Info"
                      )}
                    </Button>
                  </form>
                </TabsContent>

                {/* Questions Tab */}
                <TabsContent value="questions" className="space-y-4">
                  <form onSubmit={handleSaveQuestions} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="workAuth">Work Authorization</Label>
                      <Input
                        id="workAuth"
                        value={workAuth}
                        onChange={(e) => setWorkAuth(e.target.value)}
                        placeholder="e.g., Canadian Citizen"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="veteranStatus">Veteran Status</Label>
                      <Input
                        id="veteranStatus"
                        value={veteranStatus}
                        onChange={(e) => setVeteranStatus(e.target.value)}
                        placeholder="e.g., No"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="disabilityStatus">Disability Status</Label>
                      <Input
                        id="disabilityStatus"
                        value={disabilityStatus}
                        onChange={(e) => setDisabilityStatus(e.target.value)}
                        placeholder="e.g., No"
                      />
                    </div>

                    <Button
                      type="submit"
                      disabled={isSaving}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Save Answers"
                      )}
                    </Button>
                  </form>
                </TabsContent>

                {/* Automation Preferences Tab */}
                <TabsContent value="preferences" className="space-y-4">
                  <form onSubmit={handleSavePreferences} className="space-y-4">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                        <div>
                          <Label className="text-base font-medium text-white">Optimistic Mode</Label>
                          <p className="text-sm text-slate-400 mt-1">Automatically apply to more jobs</p>
                        </div>
                        <Switch checked={optimisticMode} onCheckedChange={setOptimisticMode} />
                      </div>

                      <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                        <div>
                          <Label className="text-base font-medium text-white">Require Approval</Label>
                          <p className="text-sm text-slate-400 mt-1">Ask for approval before applying</p>
                        </div>
                        <Switch checked={requireApproval} onCheckedChange={setRequireApproval} />
                      </div>
                    </div>

                    <Button
                      type="submit"
                      disabled={isSaving}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Save Preferences"
                      )}
                    </Button>
                  </form>
                </TabsContent>

                {/* Job Search Tab */}
                <TabsContent value="jobs" className="space-y-4">
                  <form onSubmit={handleSaveJobPreferences} className="space-y-4">
                    <div className="space-y-3">
                      <Label>Preferred Job Roles</Label>
                      <MultiSelect
                        options={JOB_TYPES}
                        selected={preferredJobTypes}
                        onSelectionChange={setPreferredJobTypes}
                        placeholder="Select job roles..."
                        searchPlaceholder="Search roles..."
                      />
                    </div>

                    <div className="space-y-3">
                      <Label>Target Companies</Label>
                      <MultiSelect
                        options={COMPANIES}
                        selected={targetCompanies}
                        onSelectionChange={setTargetCompanies}
                        placeholder="Select companies..."
                        searchPlaceholder="Search companies..."
                      />
                    </div>

                    <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                      <div>
                        <Label className="text-base font-medium text-white">Internship Only</Label>
                        <p className="text-sm text-slate-400 mt-1">Only apply to internship positions</p>
                      </div>
                      <Switch checked={internshipOnly} onCheckedChange={setInternshipOnly} />
                    </div>

                    <Button
                      type="submit"
                      disabled={isSaving}
                      className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                    >
                      {isSaving ? (
                        <>
                          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                          Saving...
                        </>
                      ) : (
                        "Save Job Preferences"
                      )}
                    </Button>
                  </form>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </div>
    </ProtectedRoute>
  )
}
