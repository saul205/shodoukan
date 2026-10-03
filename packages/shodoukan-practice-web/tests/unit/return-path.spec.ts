import { describe, expect, it } from 'vitest'
import { safeReturnPath } from '../../app/utils/return-path'

describe('safeReturnPath', () => {
  it('keeps paths inside the app', () => {
    expect(safeReturnPath('/library/entries/3?collection=2')).toBe('/library/entries/3?collection=2')
  })

  it.each([
    [undefined],
    [null],
    [''],
    ['https://evil.example/'],
    ['//evil.example/'],
    ['/\\evil.example'],
    ['/auth/callback?code=x'],
  ])('sends %s home', (path) => {
    expect(safeReturnPath(path)).toBe('/')
  })
})
