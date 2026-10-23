import { describe, expect, it } from 'vitest'
import { resolveAuthority } from '../../app/utils/auth-authority'

describe('resolveAuthority', () => {
  it('keeps an absolute issuer', () => {
    expect(resolveAuthority('http://localhost:8080/realms/shodoukan', 'http://localhost:3001'))
      .toBe('http://localhost:8080/realms/shodoukan')
  })

  it('resolves a relative issuer against the site', () => {
    expect(resolveAuthority('/idp/realms/shodoukan', 'https://shodoukan.example.ts.net'))
      .toBe('https://shodoukan.example.ts.net/idp/realms/shodoukan')
  })
})
