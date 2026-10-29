<script setup lang="ts">
import type { PracticeSentence } from '~/models/practice'
import { listSentences } from '~/services/sentences'
import { sentenceTranslation } from '~/utils/sentences'

// The sentences of the library, newest first: those that came with the
// words, and the user's own. A search (text or translation) and a filter
// for those with no linked word; each one opens in the editor. Search,
// filter and page live in the URL, as in the library.

const PAGE_SIZE = 20

const route = useRoute()
const router = useRouter()
const api = useApi()
const { glossCode } = useMeaningLang()

const search = computed<string>({
  get: () => (typeof route.query.q === 'string' ? route.query.q : ''),
  set: value => router.replace({ query: { ...route.query, q: value || undefined, page: undefined } }),
})
type Filter = 'all' | 'unlinked' | 'inactive'
const filter = computed<Filter>({
  get: () => (route.query.filter === 'unlinked' || route.query.filter === 'inactive' ? route.query.filter : 'all'),
  set: value => router.replace({ query: { ...route.query, filter: value === 'all' ? undefined : value, page: undefined } }),
})
const filters = [
  { label: 'Todas', value: 'all' },
  { label: 'Sin palabras', value: 'unlinked' },
  { label: 'Ocultas', value: 'inactive' },
]
const page = computed<number>({
  get: () => Math.max(1, Number(route.query.page) || 1),
  set: value => router.push({ query: { ...route.query, page: value } }),
})

const { data, status, error } = useAsyncData(
  'sentences',
  () => listSentences(api, {
    limit: PAGE_SIZE,
    offset: (page.value - 1) * PAGE_SIZE,
    q: search.value || undefined,
    linked: filter.value === 'unlinked' ? false : undefined,
    active: filter.value === 'inactive' ? false : undefined,
  }),
  { watch: [search, filter, page] },
)

function spans(sentence: PracticeSentence) {
  return sentence.words
    .filter(w => w.start !== null && w.end !== null)
    .map(w => ({ start: w.start as number, end: w.end as number, tone: w.entry_id ? 'primary' as const : 'neutral' as const }))
}
</script>

<template>
  <AppPanel title="Frases">
    <template #actions>
      <UButton label="Añadir frases" icon="i-lucide-plus" to="/library/sentences/new" data-testid="add-sentences" />
    </template>

    <div class="space-y-5">
      <p class="text-sm text-muted">
        Las frases de tu librería, enlazadas a las palabras que usan: cada palabra subrayada es un hueco que los ejercicios
        pueden preguntar.
      </p>
      <div class="flex flex-wrap items-center justify-end gap-3">
        <LibrarySearchInput v-model="search" class="min-w-56 flex-1 sm:max-w-sm" />
        <USelect v-model="filter" :items="filters" class="w-40" aria-label="Filtrar frases" />
      </div>

      <div v-if="status === 'pending' && !data" class="space-y-3">
        <USkeleton v-for="i in 5" :key="i" class="h-16" />
      </div>

      <UAlert
        v-else-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="No se han podido cargar tus frases"
      />

      <UEmpty
        v-else-if="data && !data.items.length"
        icon="i-lucide-quote"
        :title="search ? `Sin resultados para «${search}»` : filter === 'all' ? 'Aún no tienes frases' : 'Nada con este filtro'"
        :description="!search && filter === 'all' ? 'Llegan con las palabras que importas, o añade las tuyas.' : undefined"
        :actions="!search && filter === 'all' ? [{ label: 'Añadir frases', to: '/library/sentences/new', icon: 'i-lucide-plus' }] : undefined"
      />

      <template v-else-if="data">
        <p class="text-sm text-muted">{{ data.total }} {{ search ? 'encontradas' : 'en total' }}</p>
        <ul class="divide-y divide-default rounded-md border border-default">
          <li v-for="sentence in data.items" :key="sentence.id">
            <NuxtLink
              :to="`/library/sentences/${sentence.id}`"
              class="block p-3 hover:bg-elevated/50"
              :class="{ 'opacity-50': !sentence.is_active }"
              data-testid="sentence-row"
            >
              <p class="text-default">
                <SentenceText :text="sentence.text" :spans="spans(sentence)" />
                <AddedBadge v-if="sentence.origin === 'added'" />
              </p>
              <p v-if="sentenceTranslation(sentence, glossCode)" class="text-sm text-muted">
                {{ sentenceTranslation(sentence, glossCode) }}
              </p>
            </NuxtLink>
          </li>
        </ul>
        <UPagination
          v-if="data.total > PAGE_SIZE"
          v-model:page="page"
          :total="data.total"
          :items-per-page="PAGE_SIZE"
          class="flex justify-center"
        />
      </template>
    </div>
  </AppPanel>
</template>
