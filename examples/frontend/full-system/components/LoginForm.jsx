// examples/frontend/full-system/components/LoginForm.jsx
/**
 * Login form component with OAuth integration for GremlinsAI.
 * 
 * Supports Google OAuth2 and future Microsoft Azure OAuth2 integration
 * with seamless GremlinsAI backend authentication.
 */

import React, { useState, useEffect } from 'react'
import { signIn, getProviders, getSession, getCsrfToken } from 'next-auth/react'
import { useRouter } from 'next/router'
import Image from 'next/image'

const LoginForm = ({ csrfToken, providers }) => {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [availableProviders, setAvailableProviders] = useState([])
  const router = useRouter()

  useEffect(() => {
    // Check which OAuth providers are available from GremlinsAI backend
    checkAvailableProviders()
  }, [])

  const checkAvailableProviders = async () => {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'
      const response = await fetch(`${backendUrl}/oauth/providers`)
      
      if (response.ok) {
        const data = await response.json()
        setAvailableProviders(data.providers || [])
      }
    } catch (error) {
      console.error('Failed to fetch available providers:', error)
    }
  }

  const handleOAuthSignIn = async (providerId) => {
    setIsLoading(true)
    setError(null)

    try {
      const result = await signIn(providerId, {
        callbackUrl: router.query.callbackUrl || '/dashboard',
        redirect: false
      })

      if (result?.error) {
        setError(`Authentication failed: ${result.error}`)
      } else if (result?.url) {
        router.push(result.url)
      }
    } catch (error) {
      setError(`Sign-in error: ${error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const getProviderIcon = (providerId) => {
    const icons = {
      google: '/icons/google.svg',
      azure: '/icons/microsoft.svg'
    }
    return icons[providerId] || '/icons/default-oauth.svg'
  }

  const getProviderDisplayName = (providerId) => {
    const names = {
      google: 'Google',
      azure: 'Microsoft',
      'azure-ad': 'Microsoft'
    }
    return names[providerId] || providerId.charAt(0).toUpperCase() + providerId.slice(1)
  }

  const isProviderEnabled = (providerId) => {
    return availableProviders.some(provider => 
      provider.name === providerId && provider.enabled
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-auto flex justify-center">
            <Image
              src="/logo-gremlinsai.svg"
              alt="GremlinsAI"
              width={48}
              height={48}
              className="h-12 w-auto"
            />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to GremlinsAI
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Access your AI-powered workspace
          </p>
        </div>

        <div className="mt-8 space-y-6">
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">
                    Authentication Error
                  </h3>
                  <div className="mt-2 text-sm text-red-700">
                    {error}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {Object.values(providers || {}).map((provider) => {
              const isEnabled = isProviderEnabled(provider.id)
              
              return (
                <button
                  key={provider.name}
                  onClick={() => handleOAuthSignIn(provider.id)}
                  disabled={isLoading || !isEnabled}
                  className={`
                    group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white
                    ${isEnabled 
                      ? 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500' 
                      : 'bg-gray-300 cursor-not-allowed'
                    }
                    ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
                  `}
                >
                  <span className="absolute left-0 inset-y-0 flex items-center pl-3">
                    <Image
                      src={getProviderIcon(provider.id)}
                      alt={`${getProviderDisplayName(provider.id)} icon`}
                      width={20}
                      height={20}
                      className="h-5 w-5"
                    />
                  </span>
                  {isLoading ? (
                    <div className="flex items-center">
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Signing in...
                    </div>
                  ) : (
                    `Continue with ${getProviderDisplayName(provider.id)}`
                  )}
                </button>
              )
            })}
          </div>

          {availableProviders.length === 0 && (
            <div className="text-center">
              <p className="text-sm text-gray-500">
                No OAuth providers are currently configured.
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Please contact your administrator to set up authentication.
              </p>
            </div>
          )}

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-gray-50 text-gray-500">
                  Secure authentication powered by GremlinsAI
                </span>
              </div>
            </div>
          </div>

          <div className="text-center">
            <p className="text-xs text-gray-500">
              By signing in, you agree to our{' '}
              <a href="/terms" className="font-medium text-indigo-600 hover:text-indigo-500">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="/privacy" className="font-medium text-indigo-600 hover:text-indigo-500">
                Privacy Policy
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// Server-side props to get CSRF token and providers
export async function getServerSideProps(context) {
  const providers = await getProviders()
  const csrfToken = await getCsrfToken(context)
  
  return {
    props: {
      providers,
      csrfToken
    }
  }
}

export default LoginForm
