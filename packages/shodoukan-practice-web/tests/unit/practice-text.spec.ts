import { describe, expect, it } from 'vitest'
import type { PracticeEntry, PracticeGloss, PracticeSense } from '../../app/models/practice'
import { sensesIn } from '../../app/utils/practice-text'

let nextId = 1
function gloss(lang: string, text: string, extra: Partial<PracticeGloss> = {}): PracticeGloss {
  return { id: nextId++, text, lang, type: null, enabled: true, origin: 'imported', ...extra }
}
function sense(...glosses: PracticeGloss[]): PracticeSense {
  return { id: nextId++, pos: ['n'], misc: [], dialects: [], info: [], glosses, examples: [], notes: null }
}
function entry(...senses: PracticeSense[]): PracticeEntry {
  return {
    id: 1, source_entry_id: 1000, kanji_readings: [], readings: [], senses,
    jlpt: null, is_common: false, is_active: true, notes: null, created_at: '', updated_at: '',
  }
}

describe('sensesIn', () => {
  it('keeps the senses with a meaning in the language, enabled or not, imported or own', () => {
    const english = sense(gloss('eng', 'older brother'))
    const disabled = sense(gloss('spa', 'hermano mayor', { enabled: false }), gloss('eng', 'brother'))
    const own = sense(gloss('spa', 'primogénito', { origin: 'added' }))
    const onlyFrench = sense(gloss('fre', 'frère aîné'))
    const none = sense()

    const word = entry(english, disabled, own, onlyFrench, none)

    expect(sensesIn(word, 'spa')).toEqual([disabled, own])
    expect(sensesIn(word, 'eng')).toEqual([english, disabled])
    expect(sensesIn(word, 'ger')).toEqual([])
  })
})
