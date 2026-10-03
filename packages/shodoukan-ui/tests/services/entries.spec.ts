import { vi, describe, it, expect, beforeEach } from 'vitest'

const mockFetch = vi.fn()
vi.mock('ofetch', () => ({ $fetch: mockFetch }))

const { searchEntries, getEntry, getEntryKanji, getEntriesForKanji } = await import('../../src/services/entries')

const emptyPage = { items: [], total: 0, limit: 20, offset: 0 }

describe('searchEntries', () => {
  beforeEach(() => mockFetch.mockResolvedValue(emptyPage))

  it('calls the correct endpoint with defaults', async () => {
    await searchEntries('食べる', 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/entries/search',
      expect.objectContaining({ params: expect.objectContaining({ q: '食べる', lang: 'en', limit: 20, offset: 0 }) }),
    )
  })

  it('forwards lang, limit and offset', async () => {
    await searchEntries('food', 'http://localhost:8000', 'es', 10, 5)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ params: expect.objectContaining({ lang: 'es', limit: 10, offset: 5 }) }),
    )
  })
})

describe('getEntry', () => {
  it('calls the correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce({})
    await getEntry(42, 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/entries/42')
  })
})

describe('getEntryKanji', () => {
  it('calls the correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce([])
    await getEntryKanji(42, 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/entries/42/kanji')
  })
})

describe('getEntriesForKanji', () => {
  it('encodes the kanji literal in the URL', async () => {
    mockFetch.mockResolvedValueOnce(emptyPage)
    await getEntriesForKanji('食', 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/entries/by-kanji/%E9%A3%9F',
      expect.objectContaining({ params: expect.objectContaining({ limit: 20, offset: 0 }) }),
    )
  })
})
