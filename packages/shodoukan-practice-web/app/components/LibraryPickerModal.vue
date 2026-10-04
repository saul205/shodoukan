<script setup lang="ts">
import type { ItemKind, PracticeEntry, PracticeKanji } from '~/models/practice'
import { addToCollection } from '~/services/collections'
import { listLibraryEntries, listLibraryKanji } from '~/services/library'
import { entryHeadword, entryMeanings, entryReading, kanjiMeanings } from '~/utils/practice-text'

// Pick items of the library to add to a collection, with a search. Only what
// isn't in the collection yet is listed (`not_in_collection`); the selection
// is kept across searches. Opened with `useOverlay()`; closes with how many
// were added (0 if cancelled).
const props = defineProps<{ kind: ItemKind; collectionId: number; collectionName: string }>()
const emit = defineEmits<{ close: [added: number] }>()

const PAGE_SIZE = 20

const api = useApi()
const notify = useNotify()
const { lang, glossCode } = useMeaningLang()

const page = ref(1)
const search = ref('')
const selected = ref(new Set<number>())
const adding = ref(false)

interface Row { id: number; title: string; subtitle: string; meanings: string; active: boolean }

const { data, status } = useAsyncData(
  () => `picker-${props.kind}-${props.collectionId}`,
  async () => {
    const query = {
      limit: PAGE_SIZE,
      offset: (page.value - 1) * PAGE_SIZE,
      not_in_collection: props.collectionId,
      q: search.value || undefined,
      meaning_lang: search.value ? (props.kind === 'entries' ? glossCode.value : lang.value) : undefined,
    }
    if (props.kind === 'entries') {
      const result = await listLibraryEntries(api, query)
      return { total: result.total, rows: result.items.map(entryRow) }
    }
    const result = await listLibraryKanji(api, query)
    return { total: result.total, rows: result.items.map(kanjiRow) }
  },
  { watch: [page, search, lang] },
)

// A new search starts from its first page.
watch(search, () => {
  page.value = 1
})

function entryRow(entry: PracticeEntry): Row {
  return {
    id: entry.id,
    title: entryHeadword(entry),
    subtitle: entryReading(entry),
    meanings: entryMeanings(entry, glossCode.value).slice(0, 3).join(' · '),
    active: entry.is_active,
  }
}

function kanjiRow(kanji: PracticeKanji): Row {
  return {
    id: kanji.id,
    title: kanji.literal,
    subtitle: '',
    meanings: kanjiMeanings(kanji, lang.value).slice(0, 3).join(', '),
    active: kanji.is_active,
  }
}

function toggle(id: number, checked: boolean | 'indeterminate') {
  const next = new Set(selected.value)
  if (checked === true) next.add(id)
  else next.delete(id)
  selected.value = next
}

async function addSelected() {
  adding.value = true
  try {
    for (const id of selected.value) await addToCollection(api, props.kind, props.collectionId, id)
    emit('close', selected.value.size)
  }
  catch (error) {
    notify.failure(error, 'No se han podido añadir todos')
  }
  finally {
    adding.value = false
  }
}
</script>

<template>
  <UModal
    :title="`Añadir a «${collectionName}»`"
    description="Elige elementos de tu librería que aún no estén en la colección."
    :close="{ onClick: () => emit('close', 0) }"
    :ui="{ footer: 'justify-between', content: 'max-w-2xl' }"
  >
    <template #body>
      <LibrarySearchInput v-model="search" class="mb-3 w-full" />

      <div v-if="status === 'pending' && !data" class="space-y-2">
        <USkeleton v-for="i in 5" :key="i" class="h-10 w-full" />
      </div>

      <UEmpty
        v-else-if="!data?.rows.length && search"
        icon="i-lucide-search-x"
        :title="`Sin resultados para «${search}»`"
        description="O ya está en la colección. Prueba con otra forma de escribirlo, en kana o romaji, o con un significado."
      />

      <UEmpty
        v-else-if="!data?.rows.length"
        icon="i-lucide-library-big"
        title="No queda nada por añadir"
        description="Toda tu librería ya está en esta colección, o aún no has importado nada."
        :actions="[{ label: 'Ir al diccionario', to: '/dictionary', icon: 'i-lucide-book-open' }]"
      />

      <ul v-else class="divide-y divide-default">
        <li v-for="row in data.rows" :key="row.id" class="py-1">
          <UCheckbox
            :model-value="selected.has(row.id)"
            :ui="{ root: 'items-center w-full', wrapper: 'w-full' }"
            @update:model-value="toggle(row.id, $event)"
          >
            <template #label>
              <span class="flex w-full items-baseline gap-3" :class="{ 'opacity-60': !row.active }">
                <span class="font-japanese text-lg font-semibold text-highlighted">{{ row.title }}</span>
                <span v-if="row.subtitle" class="font-japanese text-xs text-muted">{{ row.subtitle }}</span>
                <span class="truncate text-sm text-toned">{{ row.meanings }}</span>
              </span>
            </template>
          </UCheckbox>
        </li>
      </ul>
    </template>

    <template #footer>
      <UPagination
        v-if="data && data.total > PAGE_SIZE"
        v-model:page="page"
        :total="data.total"
        :items-per-page="PAGE_SIZE"
        size="sm"
      />
      <span v-else />
      <div class="flex gap-2">
        <UButton label="Cancelar" color="neutral" variant="outline" @click="emit('close', 0)" />
        <UButton
          :label="selected.size ? `Añadir (${selected.size})` : 'Añadir'"
          icon="i-lucide-plus"
          :disabled="!selected.size"
          :loading="adding"
          @click="addSelected"
        />
      </div>
    </template>
  </UModal>
</template>
