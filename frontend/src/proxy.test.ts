import { describe, it, expect } from 'vitest'
import { NextRequest } from 'next/server'
import { proxy } from "./proxy";import { TENANT_ACCESS_COOKIE } from '@/lib/auth/tenant-session-constants'

describe('Middleware - Tenant Route Protection', () => {
  describe('For /app/* routes', () => {
    it('should redirect to /saas/login when TENANT_ACCESS_COOKIE is missing', () => {
      // Create a mock request to /app/overview without the tenant cookie
      const request = new NextRequest(new URL('http://localhost:3000/app/overview'))
      
      // Call the middleware
      const response = proxy(request)
      
      // Assert that it redirects to /saas/login
      expect(response.status).toBe(307) // Next.js redirect status
      expect(response.headers.get('location')).toBe('http://localhost:3000/saas/login')
    })

    it('should redirect to /saas/login for nested /app/* paths when cookie is missing', () => {
      // Test with a nested path
      const request = new NextRequest(new URL('http://localhost:3000/app/chatbots/123'))
      
      const response = proxy(request)
      
      expect(response.status).toBe(307)
      expect(response.headers.get('location')).toBe('http://localhost:3000/saas/login')
    })

    it('should allow access to /app/* routes when TENANT_ACCESS_COOKIE is present', () => {
      // Create a mock request with the tenant cookie
      const request = new NextRequest(new URL('http://localhost:3000/app/overview'))
      
      // Mock the cookie by setting it on the request
      request.cookies.set(TENANT_ACCESS_COOKIE, 'mock-token-value')
      
      const response = proxy(request)
      
      // Should not redirect - just pass through
      expect(response.status).toBe(200)
    })
  })

  describe('For /saas/login route', () => {
    it('should redirect authenticated users to /app/overview', () => {
      const request = new NextRequest(new URL('http://localhost:3000/saas/login'))
      
      // Set the tenant cookie to simulate authenticated user
      request.cookies.set(TENANT_ACCESS_COOKIE, 'mock-token-value')
      
      const response = proxy(request)
      
      expect(response.status).toBe(307)
      expect(response.headers.get('location')).toBe('http://localhost:3000/app/overview')
    })

    it('should allow unauthenticated users to access /saas/login', () => {
      const request = new NextRequest(new URL('http://localhost:3000/saas/login'))
      
      // No cookie set
      const response = proxy(request)
      
      // Should pass through
      expect(response.status).toBe(200)
    })
  })

  describe('Other routes', () => {
    it('should not interfere with routes outside /app/* and /saas/login', () => {
      const request = new NextRequest(new URL('http://localhost:3000/saas/signup'))
      
      const response = proxy(request)
      
      // Should just pass through
      expect(response.status).toBe(200)
    })
  })
})
