import { describe, expect, it } from 'vitest'
import type { PracticeEntry } from '../../app/models/practice'
import { kanaOf } from '../../app/utils/kana'
import {
  entryWriting,
  formatWords,
  parseMode,
  parseRepetitions,
  parseWords,
  practiceChars,
  practiceSteps,
  shuffled,
} from '../../app/utils/writing-practice'

describe('practiceSteps', () => {
  it('guides each character once', () => {
    expect(practiceSteps(['日', '本'], 'guided', 3)).toEqual([
      { index: 0, text: '日', guided: true, repetition: 0 },
      { index: 1, text: '本', guided: true, repetition: 0 },
    ])
  })

  it('guides once, then repeats freely, character by character', () => {
    const steps = practiceSteps(['日', '本'], 'guided-free', 2)

    expect(steps.map(s => [s.text, s.guided, s.repetition])).toEqual([
      ['日', true, 0], ['日', false, 1], ['日', false, 2],
      ['本', true, 0], ['本', false, 1], ['本', false, 2],
    ])
  })

  it('only repeats freely in free mode', () => {
    expect(practiceSteps(['日'], 'free', 2).map(s => s.guided)).toEqual([false, false])
  })
})

describe('practice query', () => {
  it('takes each character once, without spaces, surrogate pairs whole', () => {
    expect(practiceChars('日 本日𠮟')).toEqual(['日', '本', '𠮟'])
  })

  it('falls back to guided-then-free and two repetitions, and caps them', () => {
    expect(parseMode('free')).toBe('free')
    expect(parseMode('other')).toBe('guided-free')
    expect(parseRepetitions('3')).toBe(3)
    expect(parseRepetitions('9')).toBe(5)
    expect(parseRepetitions('0')).toBe(1)
    expect(parseRepetitions(undefined)).toBe(2)
  })

  it('shuffles a copy', () => {
    const items = [1, 2, 3]
    expect(shuffled(items, () => 0)).toEqual([2, 3, 1])
    expect(items).toEqual([1, 2, 3])
  })
})

describe('words', () => {
  it('go through the query and back, readings optional, each once', () => {
    const words = [{ text: '食べる', reading: 'たべる' }, { text: 'ひらがな' }]

    expect(formatWords(words)).toBe('食べる:たべる,ひらがな')
    expect(parseWords('食べる:たべる, ひらがな,食べる,')).toEqual(words)
    expect(parseWords(undefined)).toEqual([])
  })

  it('are written as their cards show them', () => {
    const entry = (kanji: string[], readings: string[]): PracticeEntry => ({
      id: 1, source_entry_id: 1, senses: [], jlpt: null, is_common: false, is_active: true, notes: null,
      created_at: '', updated_at: '',
      kanji_readings: kanji.map((k, i) => ({ id: i, kanji: k, info: [], enabled: true })),
      readings: readings.map((r, i) => ({ id: i, text: r, no_kanji: false, info: [], restricted_to: [], enabled: true })),
    })

    expect(entryWriting(entry(['食べる'], ['たべる']))).toEqual({ text: '食べる', reading: 'たべる' })
    expect(entryWriting(entry([], ['ひらがな']))).toEqual({ text: 'ひらがな' })
    expect(entryWriting(entry([], []))).toBeNull()
  })
})

describe('kanaOf', () => {
  it('gives the kana of the chosen rows, in table order', () => {
    expect(kanaOf(['katakana:ka', 'hiragana:a'])).toEqual([...'あいうえおカキクケコ'])
    expect(kanaOf([])).toEqual([])
  })
})
