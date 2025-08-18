// examples/frontend/full-system/components/UserProfile.jsx
/**
 * User profile component displaying OAuth user information and authentication state.
 * 
 * Shows user avatar, name, email, and provider information from OAuth authentication.
 * Integrates with GremlinsAI backend user data.
 */

import React, { useState, useEffect } from 'react'
import { useSession, signOut } from 'next-auth/react'
import Image from 'next/image'
import { makeGremlinsRequest } from '../pages/api/auth/[...nextauth]'

const UserProfile = ({ showDropdown = true, compact = false }) => {
  const { data: session, status } = useSession()
  const [userStats, setUserStats] = useState(null)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (session?.user?.gremlinsUserId) {
      fetchUserStats()
    }
  }, [session])

  const fetchUserStats = async () => {
    try {
      setIsLoading(true)
      // Fetch user statistics from GremlinsAI backend
      const stats = await makeGremlinsRequest(session, '/user/stats')
      setUserStats(stats)
    } catch (error) {
      console.error('Failed to fetch user stats:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSignOut = async () => {
    try {
      // Optionally revoke access on GremlinsAI backend
      if (session?.user?.gremlinsUserId) {
        await makeGremlinsRequest(session, '/oauth/revoke', {
          method: 'POST',
          body: JSON.stringify({ user_id: session.user.gremlinsUserId })
        })
      }
    } catch (error) {
      console.error('Failed to revoke backend access:', error)
    } finally {
      await signOut({ callbackUrl: '/auth/signin' })
    }
  }

  const getProviderIcon = (provider) => {
    const icons = {
      google: '/icons/google.svg',
      azure: '/icons/microsoft.svg',
      'azure-ad': '/icons/microsoft.svg'
    }
    return icons[provider] || '/icons/default-oauth.svg'
  }

  const getProviderDisplayName = (provider) => {
    const names = {
      google: 'Google',
      azure: 'Microsoft',
      'azure-ad': 'Microsoft'
    }
    return names[provider] || provider
  }

  if (status === 'loading') {
    return (
      <div className="flex items-center space-x-2">
        <div className="animate-pulse">
          <div className="h-8 w-8 bg-gray-300 rounded-full"></div>
        </div>
        {!compact && (
          <div className="animate-pulse">
            <div className="h-4 bg-gray-300 rounded w-24"></div>
          </div>
        )}
      </div>
    )
  }

  if (status === 'unauthenticated' || !session) {
    return null
  }

  const user = session.user

  if (compact) {
    return (
      <div className="flex items-center space-x-2">
        <div className="relative">
          <Image
            src={user.image || '/default-avatar.png'}
            alt={user.name || 'User'}
            width={32}
            height={32}
            className="h-8 w-8 rounded-full"
          />
          <div className="absolute -bottom-1 -right-1">
            <Image
              src={getProviderIcon(user.provider)}
              alt={getProviderDisplayName(user.provider)}
              width={16}
              height={16}
              className="h-4 w-4 rounded-full bg-white p-0.5"
            />
          </div>
        </div>
        <div className="text-sm font-medium text-gray-900">
          {user.name || user.email}
        </div>
      </div>
    )
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsDropdownOpen(!isDropdownOpen)}
        className="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-200"
      >
        <div className="relative">
          <Image
            src={user.image || '/default-avatar.png'}
            alt={user.name || 'User'}
            width={40}
            height={40}
            className="h-10 w-10 rounded-full"
          />
          <div className="absolute -bottom-1 -right-1">
            <Image
              src={getProviderIcon(user.provider)}
              alt={getProviderDisplayName(user.provider)}
              width={16}
              height={16}
              className="h-4 w-4 rounded-full bg-white p-0.5 border border-gray-200"
            />
          </div>
        </div>
        
        <div className="flex-1 min-w-0 text-left">
          <p className="text-sm font-medium text-gray-900 truncate">
            {user.name || 'Unknown User'}
          </p>
          <p className="text-xs text-gray-500 truncate">
            {user.email}
          </p>
          <p className="text-xs text-gray-400">
            via {getProviderDisplayName(user.provider)}
          </p>
        </div>

        {showDropdown && (
          <svg
            className={`h-5 w-5 text-gray-400 transition-transform duration-200 ${
              isDropdownOpen ? 'rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {showDropdown && isDropdownOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <Image
                src={user.image || '/default-avatar.png'}
                alt={user.name || 'User'}
                width={48}
                height={48}
                className="h-12 w-12 rounded-full"
              />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">
                  {user.name || 'Unknown User'}
                </p>
                <p className="text-sm text-gray-500 truncate">
                  {user.email}
                </p>
                <div className="flex items-center mt-1">
                  <Image
                    src={getProviderIcon(user.provider)}
                    alt={getProviderDisplayName(user.provider)}
                    width={16}
                    height={16}
                    className="h-4 w-4 mr-1"
                  />
                  <p className="text-xs text-gray-400">
                    Authenticated via {getProviderDisplayName(user.provider)}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {userStats && (
            <div className="p-4 border-b border-gray-200">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Account Stats</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Conversations</p>
                  <p className="font-medium">{userStats.conversations || 0}</p>
                </div>
                <div>
                  <p className="text-gray-500">Messages</p>
                  <p className="font-medium">{userStats.messages || 0}</p>
                </div>
                <div>
                  <p className="text-gray-500">Documents</p>
                  <p className="font-medium">{userStats.documents || 0}</p>
                </div>
                <div>
                  <p className="text-gray-500">Workflows</p>
                  <p className="font-medium">{userStats.workflows || 0}</p>
                </div>
              </div>
            </div>
          )}

          <div className="p-2">
            <button
              onClick={() => {/* Navigate to profile settings */}}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
            >
              Profile Settings
            </button>
            <button
              onClick={() => {/* Navigate to API keys */}}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
            >
              API Keys
            </button>
            <button
              onClick={() => {/* Navigate to preferences */}}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md"
            >
              Preferences
            </button>
            <hr className="my-2" />
            <button
              onClick={handleSignOut}
              className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-md"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default UserProfile
