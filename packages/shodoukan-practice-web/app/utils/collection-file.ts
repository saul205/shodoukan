import type { CollectionFile, CollectionImport } from '../models/practice'

// Collection files: downloading an export and reading one back before import.

/** A file name for the collection: its name, safe for any file system. */
export function collectionFileName(name: string): string {
  const safe = name.replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim()
  return `${safe || 'colección'}.shodoukan.json`
}

/** Saves `file` as a JSON download. */
export function downloadCollectionFile(file: CollectionFile): void {
  const blob = new Blob([JSON.stringify(file, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = collectionFileName(file.collection.name)
  link.click()
  URL.revokeObjectURL(url)
}

/**
 * The collection file in `text`, or an `Error` with a message for the user
 * when it isn't one. Only the header is checked; the API checks the items.
 */
export function parseCollectionFile(text: string): CollectionFile {
  let data: unknown
  try {
    data = JSON.parse(text)
  }
  catch {
    throw new Error('El archivo no es un JSON válido.')
  }
  const file = data as Partial<CollectionFile> | null
  if (file?.format !== 'shodoukan.collection' || typeof file.collection?.name !== 'string') {
    throw new Error('No es una colección exportada de Shodoukan.')
  }
  if (file.kind !== 'entries' && file.kind !== 'kanji') {
    throw new Error('No se sabe si la colección es de palabras o de kanji.')
  }
  return file as CollectionFile
}

/** "3 nuevos, 2 ya estaban en tu librería" and what was left out. */
export function importSummary(result: CollectionImport): string {
  const parts = [
    `${result.created} ${result.created === 1 ? 'nuevo' : 'nuevos'}`,
    `${result.existing} ${result.existing === 1 ? 'ya estaba' : 'ya estaban'} en tu librería`,
  ]
  if (result.missing.length) {
    parts.push(`${result.missing.length} ya no ${result.missing.length === 1 ? 'está' : 'están'} en el diccionario (${result.missing.join(', ')})`)
  }
  return parts.join(', ')
}
