import { describe, expect, it } from 'vitest'
import { parseMode, parseRepetitions, practiceChars, practiceSteps, shuffled } from '../../app/utils/writing-practice'

describe('practiceSteps', () => {
  it('guides each character once', () => {
    expect(practiceSteps(['日', '本'], 'guided', 3)).toEqual([
      { index: 0, char: '日', guided: true, repetition: 0 },
      { index: 1, char: '本', guided: true, repetition: 0 },
    ])
  })

  it('guides once, then repeats freely, character by character', () => {
    const steps = practiceSteps(['日', '本'], 'guided-free', 2)

    expect(steps.map(s => [s.char, s.guided, s.repetition])).toEqual([
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
