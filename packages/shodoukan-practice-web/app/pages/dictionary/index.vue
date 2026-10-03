<script setup lang="ts">
import { EntryCard, KanjiCardCompact } from 'shodoukan-ui'
import { NuxtLink } from '#components'
import { searchDictionary } from '~/services/dictionary'

// Dictionary search, like the dictionary web: the query lives in the URL
// (?q=…&page=…) and every result can be imported into the library.

const PAGE_SIZE = 20

const route = useRoute()
const router = useRouter()
const api = useApi()
const { lang, options: languages } = useMeaningLang()
const status = useImportStatus()

const query = computed(() => (typeof route.query.q === 'string' ? route.query.q : ''))
const page = computed(() => Math.max(1, Number(route.query.page) || 1))
const draft = ref(query.value)

watch(query, (q) => {
  draft.value = q
})

const { data: result, status: loading, error } = useAsyncData(
  'dictionary-search',
  async () => {
    if (!query.value) return null
    const found = await searchDictionary(api, query.value, lang.value, PAGE_SIZE, (page.value - 1) * PAGE_SIZE)
    await status.refresh(found.entries.items.map(e => e.id), found.kanji.map(k => k.literal))
    return found
  },
  { watch: [query, page, lang] },
)

function search() {
  const q = draft.value.trim()
  if (q) router.push({ query: { q } })
}

function goToPage(next: number) {
  router.push({ query: { ...route.query, page: next } })
}
</script>

<template>
  <AppPanel title="Diccionario">
    <div class="space-y-6">
      <form class="flex flex-wrap gap-2" @submit.prevent="search">
        <UInput
          v-model="draft"
          icon="i-lucide-search"
          size="lg"
          class="min-w-64 flex-1"
          placeholder="Kanji, kana, romaji o significado: 食べる, taberu, comer…"
          autofocus
        />
        <USelect v-model="lang" :items="languages" size="lg" class="w-36" aria-label="Idioma de los significados" />
        <UButton type="submit" label="Buscar" size="lg" />
      </form>

      <UEmpty
        v-if="!query"
        icon="i-lucide-book-open"
        title="Busca en el diccionario"
        description="Escribe una palabra en japonés, en romaji o su significado. Los resultados se pueden importar a tu librería."
      />

      <div v-else-if="loading === 'pending' && !result" class="space-y-3">
        <USkeleton v-for="i in 4" :key="i" class="h-28 w-full" />
      </div>

      <UAlert
        v-else-if="error"
        color="error"
        variant="soft"
        icon="i-lucide-circle-alert"
        title="No se ha podido buscar"
        description="Comprueba tu conexión e inténtalo de nuevo."
      />

      <UEmpty
        v-else-if="result && !result.entries.items.length && !result.kanji.length"
        icon="i-lucide-search-x"
        :title="`Sin resultados para «${query}»`"
        description="Prueba con otra forma de escribirla o con otro idioma."
      />

      <div v-else-if="result" class="flex flex-col-reverse gap-6 md:flex-row md:items-start">
        <section v-if="result.kanji.length" class="flex flex-col gap-3 md:w-60 md:shrink-0" aria-label="Kanji">
          <div v-for="k in result.kanji" :key="k.literal" class="flex flex-col gap-2">
            <KanjiCardCompact
              :kanji="k"
              :lang="lang"
              :link-component="NuxtLink"
              :href="`/dictionary/kanji/${k.literal}`"
            />
            <ImportButton
              :practice-id="status.kanji.value.get(k.literal)"
              :library-path="(id: number) => `/library/kanji/${id}`"
              :loading="status.isImportingKanji(k.literal)"
              class="self-center"
              @import="status.addKanji(k.literal)"
            />
          </div>
        </section>

        <section class="flex min-w-0 flex-1 flex-col gap-4" aria-label="Palabras">
          <p class="text-sm text-muted">{{ result.entries.total }} palabras</p>
          <div v-for="entry in result.entries.items" :key="entry.id" class="flex flex-col gap-2">
            <EntryCard
              :entry="entry"
              :lang="lang"
              :link-component="NuxtLink"
              :details-href="`/dictionary/entries/${entry.id}`"
              details-label="detalles →"
            />
            <ImportButton
              :practice-id="status.entries.value.get(entry.id)"
              :library-path="(id: number) => `/library/entries/${id}`"
              :loading="status.isImportingEntry(entry.id)"
              class="self-end"
              @import="status.addEntry(entry.id)"
            />
          </div>

          <UPagination
            v-if="result.entries.total > PAGE_SIZE"
            :page="page"
            :total="result.entries.total"
            :items-per-page="PAGE_SIZE"
            class="self-center"
            @update:page="goToPage"
          />
        </section>
      </div>
    </div>
  </AppPanel>
</template>
