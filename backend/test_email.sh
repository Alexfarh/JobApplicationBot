#!/bin/bash
# Email sending test script

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧪 Email Sending Test${NC}\n"

# Check if backend is running
if ! curl -s http://localhost:8000/api/profile > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Backend is not running on port 8000${NC}"
    echo "Start it with: cd backend && python -m uvicorn app.main:app --port 8000"
    exit 1
fi

echo -e "${GREEN}✓ Backend is running${NC}\n"

# Test email sending
EMAIL="${1:-test@example.com}"
echo -e "${BLUE}Sending test email to: $EMAIL${NC}\n"

RESPONSE=$(curl -X POST http://localhost:8000/api/auth/request-magic-link \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\"}" \
  -s)

echo "Response:"
echo "$RESPONSE" | jq .

# Check mode
if grep "EMAIL_MODE=prod" /Users/alexanderfarhood/Projects/WebApps/JobApplicationBot/JobApplicationBot/backend/.env > /dev/null; then
    echo -e "\n${GREEN}✓ Production mode enabled - check your email inbox${NC}"
    echo "  Email should arrive within 1-2 minutes"
    echo "  Check spam folder if you don't see it"
else
    echo -e "\n${YELLOW}ℹ️  Dev mode enabled - check backend logs for email content${NC}"
    echo "  To enable production mode:"
    echo "  1. Get SendGrid API key from https://sendgrid.com/"
    echo "  2. Update .env: EMAIL_MODE=prod and add SENDGRID_API_KEY=..."
    echo "  3. Restart backend"
fi
