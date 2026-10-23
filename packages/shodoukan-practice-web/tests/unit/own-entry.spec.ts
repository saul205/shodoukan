import { describe, expect, it } from 'vitest'
import { isKana, kanjiIn, splitForms } from '../../app/utils/own-entry'

describe('own entry helpers', () => {
  it('splits forms on commas, 、 and spaces, once each', () => {
    expect(splitForms(' さんびき、サンビキ, さんびき  ')).toEqual(['さんびき', 'サンビキ'])
    expect(splitForms('   ')).toEqual([])
  })

  it('tells kana apart', () => {
    expect(isKana('さんびき')).toBe(true)
    expect(isKana('ラーメン')).toBe(true)
    expect(isKana('三匹')).toBe(false)
    expect(isKana('sanbiki')).toBe(false)
  })

  it('lists the kanji of a spelling once each', () => {
    expect(kanjiIn('三匹の三')).toEqual(['三', '匹'])
  })
})
