import { vi, describe, it, expect, beforeEach } from 'vitest'

const mockFetch = vi.fn()
vi.mock('ofetch', () => ({ $fetch: mockFetch }))

const { search } = await import('../../src/services/search')

const emptyResult = { entries: { items: [], total: 0, limit: 20, offset: 0 }, kanji: [] }

describe('search', () => {
  beforeEach(() => mockFetch.mockResolvedValue(emptyResult))

  it('calls the correct endpoint with defaults', async () => {
    await search('食', 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/search',
      expect.objectContaining({ params: expect.objectContaining({ q: '食', lang: 'en', limit: 20, offset: 0 }) }),
    )
  })

  it('forwards lang, limit and offset', async () => {
    await search('food', 'http://localhost:8000', 'es', 5, 15)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ params: expect.objectContaining({ lang: 'es', limit: 5, offset: 15 }) }),
    )
  })

  it('returns the API response', async () => {
    mockFetch.mockResolvedValueOnce({ ...emptyResult, entries: { ...emptyResult.entries, total: 3 } })
    const result = await search('食', 'http://localhost:8000')
    expect(result.entries.total).toBe(3)
  })
})
