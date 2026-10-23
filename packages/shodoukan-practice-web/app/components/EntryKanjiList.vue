<script setup lang="ts">
import { KanjiCardCompact, type Kanji } from 'shodoukan-ui'
import { NuxtLink } from '#components'

// A word's kanji as dictionary cards, each with the import split button over
// its corner, plus "import the missing ones". `status` is the page's
// `useImportStatus()`, so the page and the cards agree. With `linkTo:
// 'library'` an imported kanji opens the user's copy.
const props = withDefaults(defineProps<{
  kanji: Kanji[]
  status: ReturnType<typeof useImportStatus>
  linkTo?: 'dictionary' | 'library'
}>(), { linkTo: 'dictionary' })

const { lang } = useMeaningLang()

/** The kanji not yet in the library. */
const missing = computed(() =>
  props.kanji.map(k => k.literal).filter(literal => !props.status.kanji.value.has(literal)),
)

function href(literal: string): string {
  const practiceId = props.status.kanji.value.get(literal)
  return props.linkTo === 'library' && practiceId !== undefined
    ? `/library/kanji/${practiceId}`
    : `/dictionary/kanji/${literal}`
}
</script>

<template>
  <section v-if="kanji.length" aria-labelledby="kanji">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h2 id="kanji" class="text-sm font-semibold uppercase tracking-wide text-muted">Kanji</h2>
      <UButton
        v-if="missing.length > 1"
        :label="`Importar los ${missing.length} que faltan`"
        icon="i-lucide-plus"
        variant="soft"
        size="sm"
        :loading="missing.some(literal => status.isBusyKanji(literal))"
        @click="status.addKanjiList(missing)"
      />
    </div>
    <!-- Same as the search results: the import button sits over each card's
         corner, beside the card's link rather than inside it. -->
    <div class="flex flex-wrap gap-3">
      <div v-for="k in kanji" :key="k.literal" class="relative flex flex-1">
        <KanjiCardCompact
          :kanji="k"
          :lang="lang"
          :link-component="NuxtLink"
          :href="href(k.literal)"
        />
        <UFieldGroup class="absolute top-2 right-2">
          <ImportButton
            icon-only
            :imported="status.kanji.value.has(k.literal)"
            :loading="status.isBusyKanji(k.literal)"
            @import="status.addKanji(k.literal)"
            @remove="status.removeKanji(k.literal)"
          />
          <CollectionMenuButton
            kind="kanji"
            icon-only
            :practice-id="status.kanji.value.get(k.literal)"
            :loading="status.isBusyKanji(k.literal)"
            @import="status.addKanji(k.literal, $event)"
          />
        </UFieldGroup>
      </div>
    </div>
  </section>
</template>
