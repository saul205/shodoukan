import type { Entry } from './entry'
import type { Kanji } from './kanji'
import type { Page } from './common'

export interface SearchResult {
  entries: Page<Entry>
  kanji: Kanji[]
}
