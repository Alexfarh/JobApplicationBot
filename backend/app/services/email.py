"""Email service for sending notifications and magic links."""
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handles email sending in dev and production modes."""
    
    def __init__(self):
        self.mode = settings.email_mode
        if self.mode == "prod":
            try:
                from sendgrid import SendGridAPIClient
                self.sendgrid_client = SendGridAPIClient(settings.sendgrid_api_key)
            except ImportError:
                logger.error("SendGrid not installed but email_mode is 'prod'")
                raise
        else:
            self.sendgrid_client = None
    
    async def send_magic_link_email(self, email: str, magic_link: str) -> bool:
        """Send magic link email to user."""
        subject = "Your Job Bot Magic Link 🔗"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">Welcome to Job Bot! 🤖</h2>
                    <p style="color: #666; font-size: 16px; line-height: 1.6;">
                        Click the link below to verify your email and log in:
                    </p>
                    <p style="margin: 30px 0;">
                        <a href="{magic_link}" style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                            Verify Email & Login
                        </a>
                    </p>
                    <p style="color: #999; font-size: 14px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px;">
                        Or copy this link: <br>
                        <code style="background-color: #f5f5f5; padding: 10px; border-radius: 3px; word-break: break-all;">
                            {magic_link}
                        </code>
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 20px;">
                        This link expires in 30 minutes.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Welcome to Job Bot!
        
        Click the link below to verify your email and log in:
        {magic_link}
        
        This link expires in 30 minutes.
        """
        
        return await self._send_email(email, subject, text_content, html_content)
    
    async def send_job_application_notification(self, email: str, job_title: str, company: str) -> bool:
        """Send notification when a job has been applied to."""
        subject = f"Application Submitted: {job_title} at {company}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">✅ Application Submitted!</h2>
                    <p style="color: #666; font-size: 16px; line-height: 1.6;">
                        Your application for <strong>{job_title}</strong> at <strong>{company}</strong> has been submitted.
                    </p>
                    <p style="color: #666; font-size: 16px; line-height: 1.6; margin-top: 20px;">
                        Good luck! We'll track the status of your application.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Application Submitted!
        
        Your application for {job_title} at {company} has been submitted.
        Good luck! We'll track the status of your application.
        """
        
        return await self._send_email(email, subject, text_content, html_content)
    
    async def send_daily_digest(self, email: str, new_jobs_count: int, applied_today: int) -> bool:
        """Send daily digest of job activity."""
        subject = f"Daily Job Digest: {new_jobs_count} new jobs found 📊"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">📊 Daily Job Digest</h2>
                    <ul style="color: #666; font-size: 16px; line-height: 1.8;">
                        <li><strong>{new_jobs_count}</strong> new jobs matching your profile</li>
                        <li><strong>{applied_today}</strong> applications submitted today</li>
                    </ul>
                    <p style="color: #666; font-size: 16px; line-height: 1.6; margin-top: 20px;">
                        Log in to the dashboard to see all opportunities.
                    </p>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Daily Job Digest
        
        - {new_jobs_count} new jobs matching your profile
        - {applied_today} applications submitted today
        
        Log in to the dashboard to see all opportunities.
        """
        
        return await self._send_email(email, subject, text_content, html_content)
    
    async def _send_email(self, to_email: str, subject: str, text_content: str, html_content: str) -> bool:
        """Internal method to send email via SendGrid or dev console."""
        if self.mode == "dev":
            logger.info(f"[DEV MODE] Email to {to_email}: {subject}")
            logger.info(f"[DEV MODE] Content:\n{text_content}")
            return True
        
        try:
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            mail = Mail(
                from_email=Email("noreply@jobbot.ai", "Job Bot"),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
            )
            
            response = self.sendgrid_client.send(mail)
            
            if 200 <= response.status_code < 300:
                logger.info(f"Email sent to {to_email}: {subject}")
                return True
            else:
                logger.error(f"Failed to send email to {to_email}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}")
            return False


# Global email service instance
email_service = EmailService()
