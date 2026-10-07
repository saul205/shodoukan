<script setup lang="ts">
import type { Page } from 'shodoukan-ui'
import type { ItemKind, PracticeEntry, PracticeKanji, SearchQuery } from '~/models/practice'
import { listCollectionEntries, listCollectionKanji, listCollections } from '~/services/collections'
import { listLibraryEntries, listLibraryKanji } from '~/services/library'
import { KANA_ROWS, kanaOf, type KanaScript } from '~/utils/kana'
import {
  DEFAULT_MODE,
  DEFAULT_REPETITIONS,
  entryWriting,
  formatIds,
  MAX_REPETITIONS,
  PRACTICE_MODES,
  type PracticeMode,
  shuffled,
} from '~/utils/writing-practice'

// Choose what to practise writing: the active kanji or words of some
// collections (or of the whole library), or rows of the kana tables; how, and
// how many times. Empezar loads them and opens /practice/play with them.
// `?kind=entries|kanji&collection=<id>` comes preselected (a collection's
// "Practicar").

const route = useRoute()
const api = useApi()
const notify = useNotify()
const toast = useToast()

/** The API's largest page. */
const PAGE_LIMIT = 100

type What = 'kanji' | 'words' | 'kana'
const preselected = Number(route.query.collection)
const what = ref<What>(route.query.kind === 'entries' ? 'words' : 'kanji')
const source = ref<'collections' | 'library'>('collections')
const collectionIds = ref<number[]>(Number.isInteger(preselected) && preselected > 0 ? [preselected] : [])
const kanaRows = ref<string[]>([])
const mode = ref<PracticeMode>(DEFAULT_MODE)
const repetitions = ref(DEFAULT_REPETITIONS)
const shuffle = ref(true)
const loading = ref(false)

const kind = computed<ItemKind>(() => (what.value === 'words' ? 'entries' : 'kanji'))
// Switching between kanji and words starts the collections over: they're different ones.
watch(what, () => {
  collectionIds.value = []
})

const { data: collections, status: collectionsStatus } = useAsyncData(
  () => `practice-collections-${kind.value}`,
  () => listCollections(api, kind.value),
  { watch: [kind] },
)
const collectionItems = computed(() => (collections.value ?? []).map(c => ({ label: c.name, value: c.id })))

const whatItems = [
  { value: 'kanji', label: 'Kanji', icon: 'i-lucide-square-pen' },
  { value: 'words', label: 'Palabras', icon: 'i-lucide-whole-word' },
  { value: 'kana', label: 'Kana', icon: 'i-lucide-languages' },
]
const sourceItems = computed(() => [
  { value: 'collections', label: 'Colecciones' },
  {
    value: 'library',
    label: 'Toda la librería',
    description: what.value === 'words' ? 'Todas tus palabras activas.' : 'Todos tus kanji activos.',
  },
])
const modeItems = PRACTICE_MODES.map(({ value, label, description }) => ({ value, label, description }))
const repetitionItems = Array.from({ length: MAX_REPETITIONS }, (_, i) => ({ value: i + 1, label: String(i + 1) }))
const SCRIPTS: { value: KanaScript; label: string }[] = [
  { value: 'hiragana', label: 'Hiragana' },
  { value: 'katakana', label: 'Katakana' },
]

function rowKey(script: KanaScript, id: string) {
  return `${script}:${id}`
}

function toggleRow(key: string, on: boolean | 'indeterminate') {
  kanaRows.value = on === true ? [...kanaRows.value, key] : kanaRows.value.filter(k => k !== key)
}

function allRows(script: KanaScript) {
  return KANA_ROWS[script].every(row => kanaRows.value.includes(rowKey(script, row.id)))
}

function toggleScript(script: KanaScript) {
  const keys = KANA_ROWS[script].map(row => rowKey(script, row.id))
  const on = !allRows(script)
  kanaRows.value = on ? [...new Set([...kanaRows.value, ...keys])] : kanaRows.value.filter(k => !keys.includes(k))
}

const canStart = computed(() => {
  if (loading.value) return false
  if (what.value === 'kana') return kanaRows.value.length > 0
  return source.value === 'library' || collectionIds.value.length > 0
})

/** Every page of a listing, one after another. */
async function allPages<T>(list: (query: SearchQuery) => Promise<Page<T>>): Promise<T[]> {
  const items: T[] = []
  for (let offset = 0; ; offset += PAGE_LIMIT) {
    const page = await list({ limit: PAGE_LIMIT, offset, active: true })
    items.push(...page.items)
    if (!page.items.length || items.length >= page.total) return items
  }
}

async function loadKanji(): Promise<PracticeKanji[]> {
  const lists = source.value === 'library'
    ? [await allPages<PracticeKanji>(query => listLibraryKanji(api, query))]
    : await Promise.all(collectionIds.value.map(id => allPages<PracticeKanji>(query => listCollectionKanji(api, id, query))))
  return unique(lists.flat())
}

async function loadWords(): Promise<PracticeEntry[]> {
  const lists = source.value === 'library'
    ? [await allPages<PracticeEntry>(query => listLibraryEntries(api, query))]
    : await Promise.all(collectionIds.value.map(id => allPages<PracticeEntry>(query => listCollectionEntries(api, id, query))))
  // Words with every spelling and reading hidden have nothing to write.
  return unique(lists.flat()).filter(entry => entryWriting(entry) !== null)
}

/** Each item once: one in several collections comes up once. */
function unique<T extends { id: number }>(items: T[]): T[] {
  const seen = new Set<number>()
  return items.filter(item => !seen.has(item.id) && seen.add(item.id))
}

async function start() {
  if (!canStart.value) return
  loading.value = true
  try {
    let query: Record<string, string>
    if (what.value === 'kana') {
      const kana = kanaOf(kanaRows.value)
      query = { chars: (shuffle.value ? shuffled(kana) : kana).join('') }
    }
    else if (what.value === 'words') {
      const words = await loadWords()
      if (!words.length) return nothingToPractise('No hay palabras activas que practicar')
      rememberPracticeItems(words.map(entry => ({ entry })))
      query = { entries: formatIds((shuffle.value ? shuffled(words) : words).map(w => w.id)) }
    }
    else {
      const kanji = await loadKanji()
      if (!kanji.length) return nothingToPractise('No hay kanji activos que practicar')
      rememberPracticeItems(kanji.map(k => ({ kanji: k })))
      query = { kanji: formatIds((shuffle.value ? shuffled(kanji) : kanji).map(k => k.id)) }
    }
    await navigateTo({
      path: '/practice/play',
      query: { ...query, mode: mode.value, reps: mode.value === 'guided' ? undefined : repetitions.value },
    })
  }
  catch (error) {
    notify.failure(error, 'No se ha podido cargar qué practicar')
  }
  finally {
    loading.value = false
  }
}

function nothingToPractise(title: string) {
  toast.add({ title, color: 'warning', icon: 'i-lucide-circle-alert' })
}
</script>

<template>
  <AppPanel title="Practicar escritura">
    <UCard class="max-w-3xl">
      <div class="space-y-6">
        <p class="text-toned">
          Aprende a escribir antes de los ejercicios, o repasa: guiado trazo a trazo, calcando el modelo o de
          memoria. La práctica no cuenta en tus estadísticas.
        </p>

        <UTabs v-model="what" :items="whatItems" :content="false" class="w-full" data-testid="practice-what" />

        <template v-if="what !== 'kana'">
          <UFormField label="De dónde">
            <URadioGroup v-model="source" :items="sourceItems" orientation="horizontal" data-testid="practice-source" />
          </UFormField>

          <UFormField v-if="source === 'collections'" :label="what === 'words' ? 'Colecciones de palabras' : 'Colecciones de kanji'">
            <USelectMenu
              v-model="collectionIds"
              :items="collectionItems"
              value-key="value"
              multiple
              :loading="collectionsStatus === 'pending'"
              placeholder="Elige colecciones"
              class="w-full"
              data-testid="practice-collections"
            />
            <template v-if="collectionsStatus === 'success' && !collectionItems.length" #help>
              No tienes colecciones {{ what === 'words' ? 'de palabras' : 'de kanji' }}.
              <ULink :to="{ path: '/collections', query: what === 'words' ? {} : { tab: 'kanji' } }" class="text-primary">Crea una</ULink>
              primero.
            </template>
          </UFormField>
        </template>

        <div v-else class="space-y-4" data-testid="practice-kana">
          <div v-for="script in SCRIPTS" :key="script.value" class="space-y-2">
            <div class="flex items-center justify-between gap-2">
              <span class="text-sm font-medium text-highlighted">{{ script.label }}</span>
              <UButton
                :label="allRows(script.value) ? 'Ninguna' : 'Todas'"
                color="neutral"
                variant="link"
                size="xs"
                :data-testid="`kana-all-${script.value}`"
                @click="toggleScript(script.value)"
              />
            </div>
            <div class="flex flex-wrap gap-1.5">
              <UCheckbox
                v-for="row in KANA_ROWS[script.value]"
                :key="row.id"
                :model-value="kanaRows.includes(rowKey(script.value, row.id))"
                :label="row.label"
                :description="row.chars"
                variant="card"
                :ui="{ root: 'px-2.5 py-1.5', label: 'font-japanese text-base', description: 'font-japanese text-xs' }"
                :data-testid="`kana-row-${script.value}-${row.id}`"
                @update:model-value="on => toggleRow(rowKey(script.value, row.id), on)"
              />
            </div>
          </div>
        </div>

        <UFormField label="Modo">
          <URadioGroup v-model="mode" :items="modeItems" variant="card" orientation="horizontal" data-testid="practice-mode" />
        </UFormField>

        <div class="flex flex-wrap items-end gap-6">
          <UFormField label="Repeticiones libres" :description="what === 'words' ? 'Por cada palabra.' : 'Por cada carácter.'">
            <USelect
              v-model="repetitions"
              :items="repetitionItems"
              :disabled="mode === 'guided'"
              class="w-24"
              data-testid="practice-repetitions"
            />
          </UFormField>
          <UCheckbox v-model="shuffle" label="Orden aleatorio" class="pb-2" data-testid="practice-shuffle" />
        </div>

        <div class="flex justify-end">
          <UButton
            label="Empezar"
            icon="i-lucide-play"
            size="lg"
            :disabled="!canStart"
            :loading="loading"
            data-testid="practice-start"
            @click="start"
          />
        </div>
      </div>
    </UCard>
  </AppPanel>
</template>
