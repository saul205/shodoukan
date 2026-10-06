<script setup lang="ts">
import type { Page } from 'shodoukan-ui'
import type { PracticeKanji, SearchQuery } from '~/models/practice'
import { listCollectionKanji, listCollections } from '~/services/collections'
import { listLibraryKanji } from '~/services/library'
import {
  DEFAULT_MODE,
  DEFAULT_REPETITIONS,
  MAX_REPETITIONS,
  PRACTICE_MODES,
  type PracticeMode,
  shuffled,
} from '~/utils/writing-practice'

// Choose what to practise writing (the active kanji of some collections, or
// of the whole library), how, and how many times; Empezar loads them and
// opens /practice/play with them. `?collection=<id>` comes preselected.

const route = useRoute()
const api = useApi()
const notify = useNotify()
const toast = useToast()

/** The API's largest page. */
const PAGE_LIMIT = 100

const preselected = Number(route.query.collection)
const source = ref<'collections' | 'library'>('collections')
const collectionIds = ref<number[]>(Number.isInteger(preselected) && preselected > 0 ? [preselected] : [])
const mode = ref<PracticeMode>(DEFAULT_MODE)
const repetitions = ref(DEFAULT_REPETITIONS)
const shuffle = ref(true)
const loading = ref(false)

const { data: collections, status: collectionsStatus } = useAsyncData('practice-kanji-collections', () =>
  listCollections(api, 'kanji'),
)
const collectionItems = computed(() => (collections.value ?? []).map(c => ({ label: c.name, value: c.id })))

const sourceItems = [
  { value: 'collections', label: 'Colecciones' },
  { value: 'library', label: 'Toda la librería', description: 'Todos tus kanji activos.' },
]
const modeItems = PRACTICE_MODES.map(({ value, label, description }) => ({ value, label, description }))
const repetitionItems = Array.from({ length: MAX_REPETITIONS }, (_, i) => ({ value: i + 1, label: String(i + 1) }))

const canStart = computed(() => !loading.value && (source.value === 'library' || collectionIds.value.length > 0))

/** Every page of a listing, one after another. */
async function allPages(list: (query: SearchQuery) => Promise<Page<PracticeKanji>>): Promise<PracticeKanji[]> {
  const items: PracticeKanji[] = []
  for (let offset = 0; ; offset += PAGE_LIMIT) {
    const page = await list({ limit: PAGE_LIMIT, offset, active: true })
    items.push(...page.items)
    if (!page.items.length || items.length >= page.total) return items
  }
}

async function start() {
  if (!canStart.value) return
  loading.value = true
  try {
    const lists = source.value === 'library'
      ? [await allPages(query => listLibraryKanji(api, query))]
      : await Promise.all(collectionIds.value.map(id => allPages(query => listCollectionKanji(api, id, query))))
    // A kanji in several collections is practised once.
    const chars = [...new Set(lists.flat().map(k => k.literal))]
    if (!chars.length) {
      toast.add({ title: 'No hay kanji activos que practicar', color: 'warning', icon: 'i-lucide-circle-alert' })
      return
    }
    await navigateTo({
      path: '/practice/play',
      query: {
        chars: (shuffle.value ? shuffled(chars) : chars).join(''),
        mode: mode.value,
        reps: mode.value === 'guided' ? undefined : repetitions.value,
      },
    })
  }
  catch (error) {
    notify.failure(error, 'No se han podido cargar los kanji')
  }
  finally {
    loading.value = false
  }
}
</script>

<template>
  <AppPanel title="Practicar escritura">
    <UCard class="max-w-3xl">
      <div class="space-y-6">
        <p class="text-toned">
          Aprende a escribir los kanji antes de los ejercicios, o repásalos: guiado trazo a trazo, calcando el
          modelo o de memoria. La práctica no cuenta en tus estadísticas.
        </p>

        <UFormField label="Qué practicar">
          <URadioGroup v-model="source" :items="sourceItems" orientation="horizontal" data-testid="practice-source" />
        </UFormField>

        <UFormField v-if="source === 'collections'" label="Colecciones de kanji">
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
            No tienes colecciones de kanji. <ULink to="/collections?tab=kanji" class="text-primary">Crea una</ULink>
            primero.
          </template>
        </UFormField>

        <UFormField label="Modo">
          <URadioGroup v-model="mode" :items="modeItems" variant="card" orientation="horizontal" data-testid="practice-mode" />
        </UFormField>

        <div class="flex flex-wrap items-end gap-6">
          <UFormField label="Repeticiones libres" description="Por cada kanji.">
            <USelect
              v-model="repetitions"
              :items="repetitionItems"
              :disabled="mode === 'guided'"
              class="w-24"
              data-testid="practice-repetitions"
            />
          </UFormField>
          <UCheckbox v-model="shuffle" label="Orden aleatorio" class="pb-2" />
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
