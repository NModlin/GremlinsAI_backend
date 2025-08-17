# Google OAuth2 Setup Guide for GremlinsAI

This guide walks you through setting up Google OAuth2 authentication for the GremlinsAI backend system.

## Prerequisites

- Google Cloud Console account
- GremlinsAI backend running locally or deployed
- Admin access to configure OAuth settings

## Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Sign in with your Google account

2. **Create a New Project** (or select existing)
   - Click on the project dropdown at the top
   - Click "New Project"
   - Enter project name: `gremlinsai-oauth` (or your preferred name)
   - Click "Create"

3. **Select Your Project**
   - Make sure your new project is selected in the project dropdown

## Step 2: Enable Google+ API

1. **Navigate to APIs & Services**
   - In the left sidebar, click "APIs & Services" > "Library"

2. **Enable Required APIs**
   - Search for "Google+ API" and enable it
   - Alternatively, search for "Google Identity" and enable "Google Identity Toolkit API"
   - Also enable "People API" for profile information

## Step 3: Configure OAuth Consent Screen

1. **Go to OAuth Consent Screen**
   - In the left sidebar, click "APIs & Services" > "OAuth consent screen"

2. **Choose User Type**
   - Select "External" for public applications
   - Select "Internal" if you're using Google Workspace and want to restrict to your organization
   - Click "Create"

3. **Fill App Information**
   ```
   App name: GremlinsAI
   User support email: your-email@example.com
   App logo: (optional - upload your logo)
   App domain: localhost:8000 (for development) or your domain
   Authorized domains: 
     - localhost (for development)
     - your-domain.com (for production)
   Developer contact information: your-email@example.com
   ```

4. **Scopes Configuration**
   - Click "Add or Remove Scopes"
   - Add these scopes:
     - `openid`
     - `email`
     - `profile`
   - Click "Update"

5. **Test Users** (for External apps in testing)
   - Add test user emails that can access your app during development
   - Add your own email and any developer emails

6. **Review and Submit**
   - Review all information
   - Click "Back to Dashboard"

## Step 4: Create OAuth 2.0 Credentials

1. **Go to Credentials**
   - In the left sidebar, click "APIs & Services" > "Credentials"

2. **Create OAuth Client ID**
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application"

3. **Configure OAuth Client**
   ```
   Name: GremlinsAI Backend OAuth
   
   Authorized JavaScript origins:
   - http://localhost:3000 (for frontend development)
   - http://localhost:8000 (for backend development)
   - https://your-frontend-domain.com (for production)
   
   Authorized redirect URIs:
   - http://localhost:8000/api/v1/oauth/google/callback (backend)
   - http://localhost:3000/api/auth/callback/google (NextAuth frontend)
   - https://your-backend-domain.com/api/v1/oauth/google/callback (production backend)
   - https://your-frontend-domain.com/api/auth/callback/google (production frontend)
   ```

4. **Save Credentials**
   - Click "Create"
   - **Important**: Copy the Client ID and Client Secret immediately
   - Download the JSON file for backup

## Step 5: Configure GremlinsAI Backend

1. **Update Environment Variables**
   
   Add to your `.env` file:
   ```bash
   # Google OAuth2 Configuration
   GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="your-google-client-secret"
   OAUTH_REDIRECT_URL="http://localhost:8000/api/v1/oauth/google/callback"
   
   # Security Settings
   SECRET_KEY="your-secret-key-change-in-production"
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

2. **For Production Deployment**
   ```bash
   # Production OAuth Configuration
   GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
   GOOGLE_CLIENT_SECRET="your-google-client-secret"
   OAUTH_REDIRECT_URL="https://your-domain.com/api/v1/oauth/google/callback"
   SECRET_KEY="your-secure-production-secret-key"
   ```

## Step 6: Configure Frontend (NextAuth)

1. **Update Frontend Environment Variables**
   
   For the full-system example (`examples/frontend/full-system/.env.local`):
   ```bash
   # NextAuth Configuration
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=your-nextauth-secret
   
   # Google OAuth
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   
   # GremlinsAI Backend
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
   ```

2. **For Production Frontend**
   ```bash
   NEXTAUTH_URL=https://your-frontend-domain.com
   NEXTAUTH_SECRET=your-secure-nextauth-secret
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   NEXT_PUBLIC_API_BASE_URL=https://your-backend-domain.com/api/v1
   ```

## Step 7: Run Database Migration

1. **Apply OAuth Migration**
   ```bash
   # Navigate to GremlinsAI backend directory
   cd GremlinsAI_backend
   
   # Run the migration
   alembic upgrade head
   ```

2. **Verify Migration**
   ```bash
   # Check current migration version
   alembic current
   
   # Should show: oauth_users_2024 (head)
   ```

## Step 8: Test OAuth Integration

1. **Start GremlinsAI Backend**
   ```bash
   uvicorn app.main:app --reload
   ```

2. **Test OAuth Status**
   ```bash
   curl http://localhost:8000/api/v1/oauth/status
   ```
   
   Should return:
   ```json
   {
     "oauth_enabled": true,
     "providers": {
       "google": {
         "enabled": true,
         "configured": true
       }
     }
   }
   ```

3. **Test OAuth Providers**
   ```bash
   curl http://localhost:8000/api/v1/oauth/providers
   ```

4. **Test Google Login Flow**
   - Visit: `http://localhost:8000/api/v1/oauth/google/login`
   - Should redirect to Google OAuth consent screen
   - After consent, should redirect back with user info and API key

## Step 9: Frontend Testing

1. **Start Frontend** (if using full-system example)
   ```bash
   cd examples/frontend/full-system
   npm install
   npm run dev
   ```

2. **Test Login**
   - Visit: `http://localhost:3000/auth/signin`
   - Click "Continue with Google"
   - Complete OAuth flow
   - Should be redirected to dashboard with user info

## Security Best Practices

### Development
- Use `http://localhost` URLs only for development
- Keep Client Secret secure and never commit to version control
- Use different OAuth clients for development and production

### Production
- Always use HTTPS URLs in production
- Store secrets in secure environment variables or secret management systems
- Regularly rotate Client Secrets
- Monitor OAuth usage and failed attempts
- Implement rate limiting on OAuth endpoints

### Domain Verification
- Verify ownership of domains in Google Cloud Console
- Only add necessary redirect URIs
- Remove development URLs from production OAuth clients

## Troubleshooting

### Common Issues

1. **"redirect_uri_mismatch" Error**
   - Ensure redirect URI in Google Cloud Console exactly matches the one in your request
   - Check for trailing slashes, http vs https, port numbers

2. **"invalid_client" Error**
   - Verify Client ID and Client Secret are correct
   - Check that the OAuth client is enabled

3. **"access_blocked" Error**
   - App may be in testing mode with restricted users
   - Add test users or publish the app

4. **Backend Authentication Fails**
   - Check that GremlinsAI backend OAuth endpoints are working
   - Verify database migration was applied
   - Check backend logs for detailed error messages

### Debug Commands

```bash
# Check OAuth configuration
curl http://localhost:8000/api/v1/oauth/status

# Check available providers
curl http://localhost:8000/api/v1/oauth/providers

# Test database connection
alembic current

# Check backend logs
tail -f app.log
```

## Next Steps

After successful setup:

1. **Test with Multiple Users**: Invite team members to test the OAuth flow
2. **Configure Azure OAuth**: Follow similar steps for Microsoft Azure integration
3. **Set Up Production**: Deploy with proper HTTPS and domain configuration
4. **Monitor Usage**: Set up logging and monitoring for OAuth authentication
5. **Backup Credentials**: Securely store OAuth credentials and recovery codes

## Support

If you encounter issues:

1. Check the [GremlinsAI documentation](../README.md)
2. Review Google Cloud Console OAuth documentation
3. Check backend logs for detailed error messages
4. Verify all environment variables are set correctly

For additional help, refer to the GremlinsAI community resources or create an issue in the project repository.
