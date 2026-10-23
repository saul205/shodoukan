/**
 * A path inside this app to go back to after signing in. Anything else
 * (absolute or protocol-relative URLs) becomes "/", so the sign-in state
 * can't be used to redirect to another site.
 */
export function safeReturnPath(path: string | undefined | null): string {
  if (!path || !path.startsWith('/') || path.startsWith('//') || path.startsWith('/\\')) return '/'
  if (path.startsWith('/auth/callback')) return '/'
  return path
}
