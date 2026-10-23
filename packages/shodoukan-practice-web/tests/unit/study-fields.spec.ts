import { describe, expect, it } from 'vitest'
import { defaultChoiceSettings, directionKey, directionLabel, STUDY_FIELDS } from '../../app/utils/study-fields'

describe('study fields', () => {
  it('names a direction by its fields', () => {
    expect(directionLabel({ prompt: ['writing', 'reading'], answer: 'meaning' }))
      .toBe('Escritura + Lectura → Significado')
  })

  it('treats the shown fields of a direction as a set', () => {
    expect(directionKey({ prompt: ['writing', 'reading'], answer: 'meaning' }))
      .toBe(directionKey({ prompt: ['reading', 'writing'], answer: 'meaning' }))
    expect(directionKey({ prompt: ['writing'], answer: 'meaning' }))
      .not.toBe(directionKey({ prompt: ['meaning'], answer: 'writing' }))
  })

  it('defaults use only the fields of their kind', () => {
    for (const kind of ['entries', 'kanji'] as const) {
      const settings = defaultChoiceSettings(kind)
      const used = [...settings.back_fields, ...settings.directions.flatMap(d => [...d.prompt, d.answer])]
      expect(used.every(field => STUDY_FIELDS[kind].includes(field))).toBe(true)
    }
  })
})
