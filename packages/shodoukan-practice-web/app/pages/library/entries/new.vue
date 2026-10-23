<script setup lang="ts">
import type { Entry } from 'shodoukan-ui'
import { getCollection } from '~/services/collections'
import { searchDictionary } from '~/services/dictionary'
import { createOwnEntry } from '~/services/library'
import { isKana, splitForms } from '~/utils/own-entry'

// A word of the user's own, for what the dictionary doesn't have (counters
// with their numbers, phrases from class): its spellings, readings and first
// meaning. Opened from a collection (`?collection=<id>`), it goes into it.
// While typing, words the dictionary already has with that form are shown,
// to import one instead.

const route = useRoute()
const api = useApi()
const notify = useNotify()
const { lang, glossCode, options: languages } = useMeaningLang()
const back = useBackLink('entries')

const collectionId = computed(() => {
  const id = Number(route.query.collection)
  return Number.isInteger(id) && id > 0 ? id : null
})
const { data: collection } = useAsyncData(
  () => `new-entry-collection-${collectionId.value}`,
  () => (collectionId.value === null ? Promise.resolve(null) : getCollection(api, 'entries', collectionId.value)),
  { watch: [collectionId] },
)

const MAX_MEANING = 500

const spellingsText = ref('')
const readingsText = ref('')
const meaning = ref('')
const creating = ref(false)

const spellings = computed(() => splitForms(spellingsText.value))
const readings = computed(() => splitForms(readingsText.value))
const readingsInvalid = computed(() => readings.value.some(r => !isKana(r)))
const languageLabel = computed(() => languages.find(l => l.value === lang.value)?.label ?? lang.value)

const canCreate = computed(() =>
  !creating.value
  && readings.value.length > 0
  && !readingsInvalid.value
  && meaning.value.trim().length > 0
  && meaning.value.trim().length <= MAX_MEANING,
)

// The dictionary's words written (or, without a spelling, read) the same way.
const lookup = computed(() => spellings.value[0] ?? (readingsInvalid.value ? undefined : readings.value[0]))
const LOOKUP_DELAY_MS = 400
const debouncedLookup = ref<string | undefined>()
let timer: ReturnType<typeof setTimeout> | undefined
watch(lookup, (form) => {
  clearTimeout(timer)
  timer = setTimeout(() => (debouncedLookup.value = form), LOOKUP_DELAY_MS)
})
onBeforeUnmount(() => clearTimeout(timer))
const { data: matches } = useAsyncData(
  () => `new-entry-matches-${debouncedLookup.value ?? ''}`,
  async (): Promise<Entry[]> => {
    const form = debouncedLookup.value
    if (!form) return []
    const result = await searchDictionary(api, form, lang.value, 10)
    return result.entries.items
      .filter(e => e.kanji_readings.some(k => k.kanji === form) || e.readings.some(r => r.text === form))
      .slice(0, 3)
  },
  { watch: [debouncedLookup], default: () => [] },
)

function headword(entry: Entry): string {
  return entry.kanji_readings[0]?.kanji ?? entry.readings[0]?.text ?? ''
}

function firstMeaning(entry: Entry): string {
  for (const sense of entry.senses) {
    const gloss = sense.glosses.find(g => g.lang === glossCode.value)
    if (gloss) return gloss.text
  }
  return ''
}

async function create() {
  if (!canCreate.value) return
  creating.value = true
  try {
    const entry = await createOwnEntry(api, {
      spellings: spellings.value,
      readings: readings.value,
      meaning: meaning.value.trim(),
      lang: glossCode.value,
      collection_ids: collectionId.value === null ? [] : [collectionId.value],
    })
    notify.success('Palabra creada')
    await navigateTo({
      path: `/library/entries/${entry.id}`,
      query: collectionId.value === null ? {} : { collection: collectionId.value },
    })
  }
  catch (error) {
    notify.failure(error, 'No se ha podido crear')
  }
  finally {
    creating.value = false
  }
}
</script>

<template>
  <AppPanel title="Nueva palabra">
    <template #leading>
      <UButton :to="back.to" icon="i-lucide-arrow-left" color="neutral" variant="ghost" :aria-label="back.label" />
    </template>

    <div class="mx-auto max-w-xl space-y-6">
      <p class="text-sm text-muted">
        Para lo que el diccionario no tiene, como un número con su contador (三匹). Luego podrás
        añadirle más significados, ejemplos y notas como a cualquier otra palabra.
      </p>

      <form class="space-y-4" data-testid="new-entry-form" @submit.prevent="create">
        <UFormField label="Escritura" help="Opcional; varias separadas por comas, la habitual primero." name="spellings">
          <UInput v-model="spellingsText" placeholder="三匹" class="w-full font-japanese" data-testid="spellings" />
        </UFormField>

        <UFormField
          label="Lectura"
          help="En kana; varias separadas por comas."
          :error="readingsInvalid ? 'Escribe las lecturas en hiragana o katakana.' : undefined"
          name="readings"
          required
        >
          <UInput v-model="readingsText" placeholder="さんびき" class="w-full font-japanese" data-testid="readings" />
        </UFormField>

        <UFormField :label="`Significado (en ${languageLabel})`" help="El primero; podrás añadir más." name="meaning" required>
          <UInput v-model="meaning" placeholder="three (small animals)" class="w-full" :maxlength="MAX_MEANING" data-testid="meaning" />
        </UFormField>

        <p v-if="collection" class="text-sm text-muted">Se añadirá a la colección <strong>{{ collection.name }}</strong>.</p>

        <UAlert
          v-if="matches?.length"
          color="warning"
          variant="subtle"
          icon="i-lucide-book-open"
          title="El diccionario ya tiene esta palabra"
          description="Puedes importarla en lugar de crearla; si es otra, créala igualmente."
          data-testid="dictionary-matches"
        >
          <template #actions>
            <UButton
              v-for="match in matches"
              :key="match.id"
              :to="`/dictionary/entries/${match.id}`"
              :label="`${headword(match)} · ${firstMeaning(match)}`"
              size="sm"
              color="neutral"
              variant="outline"
              class="font-japanese"
            />
          </template>
        </UAlert>

        <div class="flex justify-end gap-2">
          <UButton :to="back.to" label="Cancelar" color="neutral" variant="ghost" />
          <UButton type="submit" label="Crear palabra" icon="i-lucide-plus" :loading="creating" :disabled="!canCreate" />
        </div>
      </form>
    </div>
  </AppPanel>
</template>
