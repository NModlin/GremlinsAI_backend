// examples/frontend/full-system/pages/api/auth/[...nextauth].js
/**
 * NextAuth.js configuration for GremlinsAI OAuth integration.
 * 
 * This configuration integrates with the GremlinsAI backend OAuth system,
 * supporting Google OAuth2 and future Microsoft Azure OAuth2.
 */

import NextAuth from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import AzureADProvider from 'next-auth/providers/azure-ad'

export default NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      authorization: {
        params: {
          scope: 'openid email profile',
          prompt: 'consent',
          access_type: 'offline',
          response_type: 'code'
        }
      }
    }),
    
    // Microsoft Azure AD Provider (for future use)
    ...(process.env.AZURE_CLIENT_ID && process.env.AZURE_CLIENT_SECRET && process.env.AZURE_TENANT_ID ? [
      AzureADProvider({
        clientId: process.env.AZURE_CLIENT_ID,
        clientSecret: process.env.AZURE_CLIENT_SECRET,
        tenantId: process.env.AZURE_TENANT_ID,
        authorization: {
          params: {
            scope: 'openid email profile User.Read'
          }
        }
      })
    ] : [])
  ],

  callbacks: {
    async signIn({ user, account, profile, email, credentials }) {
      try {
        // Exchange OAuth token with GremlinsAI backend
        const backendResponse = await exchangeTokenWithBackend(account, profile)
        
        if (backendResponse.success) {
          // Store GremlinsAI API key in user object
          user.gremlinsApiKey = backendResponse.api_key
          user.gremlinsUserId = backendResponse.user.id
          user.provider = account.provider
          return true
        }
        
        console.error('Failed to authenticate with GremlinsAI backend:', backendResponse)
        return false
        
      } catch (error) {
        console.error('Sign-in error:', error)
        return false
      }
    },

    async jwt({ token, user, account }) {
      // Persist GremlinsAI API key in JWT token
      if (user) {
        token.gremlinsApiKey = user.gremlinsApiKey
        token.gremlinsUserId = user.gremlinsUserId
        token.provider = user.provider
      }
      return token
    },

    async session({ session, token }) {
      // Send GremlinsAI API key to client
      session.user.gremlinsApiKey = token.gremlinsApiKey
      session.user.gremlinsUserId = token.gremlinsUserId
      session.user.provider = token.provider
      return session
    },

    async redirect({ url, baseUrl }) {
      // Redirect to dashboard after successful authentication
      if (url.startsWith('/')) return `${baseUrl}${url}`
      else if (new URL(url).origin === baseUrl) return url
      return `${baseUrl}/dashboard`
    }
  },

  pages: {
    signIn: '/auth/signin',
    error: '/auth/error'
  },

  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  jwt: {
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  secret: process.env.NEXTAUTH_SECRET,

  debug: process.env.NODE_ENV === 'development'
})

/**
 * Exchange OAuth token with GremlinsAI backend to get API key
 */
async function exchangeTokenWithBackend(account, profile) {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'
    
    // Prepare user info for GremlinsAI backend
    const userInfo = {
      id: profile.sub || profile.id,
      email: profile.email,
      name: profile.name,
      picture: profile.picture || profile.image,
      provider: account.provider
    }
    
    // Call GremlinsAI backend to create/update OAuth user
    const response = await fetch(`${backendUrl}/oauth/${account.provider}/exchange`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        access_token: account.access_token,
        user_info: userInfo,
        provider: account.provider
      })
    })
    
    if (!response.ok) {
      throw new Error(`Backend exchange failed: ${response.status} ${response.statusText}`)
    }
    
    const data = await response.json()
    return data
    
  } catch (error) {
    console.error('Token exchange error:', error)
    return { success: false, error: error.message }
  }
}

/**
 * Get GremlinsAI API client configured with user's API key
 */
export function getGremlinsAPIClient(session) {
  if (!session?.user?.gremlinsApiKey) {
    throw new Error('No GremlinsAI API key found in session')
  }
  
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'
  
  return {
    baseUrl,
    apiKey: session.user.gremlinsApiKey,
    headers: {
      'Authorization': `Bearer ${session.user.gremlinsApiKey}`,
      'Content-Type': 'application/json'
    }
  }
}

/**
 * Utility function to make authenticated requests to GremlinsAI backend
 */
export async function makeGremlinsRequest(session, endpoint, options = {}) {
  const client = getGremlinsAPIClient(session)
  
  const response = await fetch(`${client.baseUrl}${endpoint}`, {
    ...options,
    headers: {
      ...client.headers,
      ...options.headers
    }
  })
  
  if (!response.ok) {
    throw new Error(`GremlinsAI API error: ${response.status} ${response.statusText}`)
  }
  
  return response.json()
}
