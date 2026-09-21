import { vi, describe, it, expect, beforeEach } from 'vitest'

const mockFetch = vi.fn()
vi.mock('ofetch', () => ({ $fetch: mockFetch }))

const { searchKanji, getKanji } = await import('../../services/kanji')

const emptyPage = { items: [], total: 0, limit: 20, offset: 0 }

describe('searchKanji', () => {
  beforeEach(() => mockFetch.mockResolvedValue(emptyPage))

  it('calls the correct endpoint', async () => {
    await searchKanji({ q: '食', lang: 'en' }, 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith(
      'http://localhost:8000/kanji/search',
      expect.objectContaining({ params: expect.objectContaining({ q: '食', lang: 'en' }) }),
    )
  })

  it('supports grade and jlpt filters', async () => {
    await searchKanji({ grade: 2, jlpt: 4 }, 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ params: expect.objectContaining({ grade: 2, jlpt: 4 }) }),
    )
  })

  it('returns the API response', async () => {
    mockFetch.mockResolvedValueOnce({ items: [], total: 42, limit: 20, offset: 0 })
    const result = await searchKanji({ q: '火' }, 'http://localhost:8000')
    expect(result.total).toBe(42)
  })
})

describe('getKanji', () => {
  it('calls the correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce({})
    await getKanji('食', 'http://localhost:8000')
    expect(mockFetch).toHaveBeenCalledWith('http://localhost:8000/kanji/%E9%A3%9F')
  })
})
