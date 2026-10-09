import { describe, expect, it } from 'vitest'
import { collectionFileName, importSummary, parseCollectionFile } from '../../app/utils/collection-file'

const header = { format: 'shodoukan.collection', version: 1, kind: 'entries', exported_at: null }

describe('collection files', () => {
  it('names the file after the collection, safely', () => {
    expect(collectionFileName('JLPT N5')).toBe('JLPT N5.shodoukan.json')
    expect(collectionFileName('a/b: c?')).toBe('a b c.shodoukan.json')
    expect(collectionFileName(' / ')).toBe('colección.shodoukan.json')
  })

  it('reads an exported collection', () => {
    const file = { ...header, collection: { name: 'verbos', items: [] } }
    expect(parseCollectionFile(JSON.stringify(file))).toEqual(file)
  })

  it('rejects what is not an exported collection', () => {
    expect(() => parseCollectionFile('{ nope')).toThrow('JSON válido')
    expect(() => parseCollectionFile('null')).toThrow('No es una colección')
    expect(() => parseCollectionFile(JSON.stringify({ ...header, format: 'x', collection: { name: 'a' } }))).toThrow('No es una colección')
    expect(() => parseCollectionFile(JSON.stringify({ ...header, kind: 'tags', collection: { name: 'a' } }))).toThrow('palabras o de kanji')
  })

  it('sums up what an import did', () => {
    const collection = { id: 1, name: 'N5', description: null, created_at: '', updated_at: '' }
    expect(importSummary({ collection, created: 1, existing: 2, missing: [] }))
      .toBe('1 nuevo, 2 ya estaban en tu librería')
    expect(importSummary({ collection, created: 0, existing: 1, missing: ['𠮟'] }))
      .toBe('0 nuevos, 1 ya estaba en tu librería, 1 ya no está en el diccionario (𠮟)')
  })
})
