// The kana tables, by row (gojūon order), for practising them without the
// library: KanjiVG draws every kana.

export interface KanaRow {
  id: string
  /** The row's first kana, as it's named ("the か row"). */
  label: string
  chars: string
}

export type KanaScript = 'hiragana' | 'katakana'

export const KANA_ROWS: Record<KanaScript, KanaRow[]> = {
  hiragana: [
    { id: 'a', label: 'あ', chars: 'あいうえお' },
    { id: 'ka', label: 'か', chars: 'かきくけこ' },
    { id: 'sa', label: 'さ', chars: 'さしすせそ' },
    { id: 'ta', label: 'た', chars: 'たちつてと' },
    { id: 'na', label: 'な', chars: 'なにぬねの' },
    { id: 'ha', label: 'は', chars: 'はひふへほ' },
    { id: 'ma', label: 'ま', chars: 'まみむめも' },
    { id: 'ya', label: 'や', chars: 'やゆよ' },
    { id: 'ra', label: 'ら', chars: 'らりるれろ' },
    { id: 'wa', label: 'わ', chars: 'わをん' },
    { id: 'ga', label: 'が', chars: 'がぎぐげご' },
    { id: 'za', label: 'ざ', chars: 'ざじずぜぞ' },
    { id: 'da', label: 'だ', chars: 'だぢづでど' },
    { id: 'ba', label: 'ば', chars: 'ばびぶべぼ' },
    { id: 'pa', label: 'ぱ', chars: 'ぱぴぷぺぽ' },
    { id: 'small', label: 'ゃ', chars: 'ぁぃぅぇぉゃゅょっ' },
  ],
  katakana: [
    { id: 'a', label: 'ア', chars: 'アイウエオ' },
    { id: 'ka', label: 'カ', chars: 'カキクケコ' },
    { id: 'sa', label: 'サ', chars: 'サシスセソ' },
    { id: 'ta', label: 'タ', chars: 'タチツテト' },
    { id: 'na', label: 'ナ', chars: 'ナニヌネノ' },
    { id: 'ha', label: 'ハ', chars: 'ハヒフヘホ' },
    { id: 'ma', label: 'マ', chars: 'マミムメモ' },
    { id: 'ya', label: 'ヤ', chars: 'ヤユヨ' },
    { id: 'ra', label: 'ラ', chars: 'ラリルレロ' },
    { id: 'wa', label: 'ワ', chars: 'ワヲン' },
    { id: 'ga', label: 'ガ', chars: 'ガギグゲゴ' },
    { id: 'za', label: 'ザ', chars: 'ザジズゼゾ' },
    { id: 'da', label: 'ダ', chars: 'ダヂヅデド' },
    { id: 'ba', label: 'バ', chars: 'バビブベボヴ' },
    { id: 'pa', label: 'パ', chars: 'パピプペポ' },
    { id: 'small', label: 'ャ', chars: 'ァィゥェォャュョッー' },
  ],
}

/** The kana of the chosen rows (`<script>:<row id>`), in table order. */
export function kanaOf(rows: string[]): string[] {
  const chosen = new Set(rows)
  return (Object.keys(KANA_ROWS) as KanaScript[]).flatMap(script =>
    KANA_ROWS[script].filter(row => chosen.has(`${script}:${row.id}`)).flatMap(row => Array.from(row.chars)),
  )
}
