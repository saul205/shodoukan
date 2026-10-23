/**
 * The identity provider's absolute URL. The issuer can be absolute (local
 * dev: Keycloak on its own port) or relative to the site (deployed: Keycloak
 * behind the same host at /idp), so one static build works on any host.
 */
export function resolveAuthority(issuer: string, origin: string): string {
  return new URL(issuer, origin).href
}
