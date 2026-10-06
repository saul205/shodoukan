<script setup lang="ts">
import type { KanjiPart, PracticeKanji, PracticeReadingItem } from '~/models/practice'

// A library kanji: the character with its data, readings, stroke order and
// meanings in the meaning language. Editable (reading chips, meaning
// switches, own meanings: it emits, the page saves) or `view-only`, showing
// only what the user keeps enabled, as in the item detail opened from a
// session.
const props = withDefaults(defineProps<{
  kanji: PracticeKanji
  viewOnly?: boolean
  saving?: boolean
}>(), { viewOnly: false, saving: false })

const emit = defineEmits<{
  'toggle': [part: KanjiPart, id: number, enabled: boolean]
  'add-meaning': [text: string]
  'edit-meaning': [meaningId: number, text: string]
  'remove-meaning': [meaningId: number]
}>()

const { lang, options: languages } = useMeaningLang()
const languageLabel = computed(() => languages.find(l => l.value === lang.value)?.label ?? lang.value)
const meanings = computed(() => props.kanji.meanings.filter(m => m.lang === lang.value))

const readingGroups = computed<{ label: string; items: PracticeReadingItem[] }[]>(() =>
  [
    { label: 'Kun\'yomi', items: props.kanji.kun_readings },
    { label: 'On\'yomi', items: props.kanji.on_readings },
    { label: 'Nanori', items: props.kanji.nanori },
  ].filter(group => (props.viewOnly ? group.items.some(r => r.enabled) : group.items.length)),
)
</script>

<template>
  <div class="space-y-8">
    <!-- Kanji with its data below and its readings beside it, then the stroke
         order across; one column on phones (kanji, data, readings, strokes). -->
    <div class="grid gap-x-8 gap-y-6 sm:grid-cols-[auto_1fr]">
      <span class="font-japanese text-8xl leading-none font-bold text-highlighted">{{ kanji.literal }}</span>

      <dl class="grid grid-cols-2 content-start gap-x-4 gap-y-2 text-sm">
        <div>
          <dt class="text-xs uppercase tracking-wide text-dimmed">Trazos</dt>
          <dd class="text-toned">{{ kanji.stroke_count }}</dd>
        </div>
        <div v-if="kanji.grade">
          <dt class="text-xs uppercase tracking-wide text-dimmed">Grado</dt>
          <dd class="text-toned">{{ kanji.grade }}</dd>
        </div>
        <div v-if="kanji.jlpt">
          <dt class="text-xs uppercase tracking-wide text-dimmed">JLPT</dt>
          <dd class="text-toned">N{{ kanji.jlpt }}</dd>
        </div>
      </dl>

      <section aria-labelledby="readings" class="space-y-3 sm:col-start-2 sm:row-span-2 sm:row-start-1">
        <h2 id="readings" class="text-sm font-semibold uppercase tracking-wide text-muted">Lecturas</h2>
        <div v-for="group in readingGroups" :key="group.label" class="flex items-start gap-3">
          <span class="w-20 shrink-0 pt-1.5 text-xs uppercase tracking-wide text-dimmed">{{ group.label }}</span>
          <ReadingChips
            :readings="group.items"
            :view-only="viewOnly"
            :disabled="saving"
            @toggle="(readingId, enabled) => emit('toggle', 'readings', readingId, enabled)"
          />
        </div>
      </section>

      <section aria-labelledby="strokes" class="space-y-3 sm:col-span-2">
        <h2 id="strokes" class="text-sm font-semibold uppercase tracking-wide text-muted">Orden de trazos</h2>
        <KanjiStrokeOrder :literal="kanji.literal" :size="128" cell-size="4.5rem" />
      </section>
    </div>

    <section aria-labelledby="meanings" class="space-y-3">
      <div class="flex items-baseline justify-between gap-2">
        <h2 id="meanings" class="text-sm font-semibold uppercase tracking-wide text-muted">Significados</h2>
        <span class="text-xs text-dimmed">en {{ languageLabel }} · cámbialo en el menú lateral</span>
      </div>
      <UCard>
        <MeaningList
          :meanings="meanings"
          :view-only="viewOnly"
          :disabled="saving"
          @toggle="(meaningId, enabled) => emit('toggle', 'meanings', meaningId, enabled)"
          @add="text => emit('add-meaning', text)"
          @edit="(meaningId, text) => emit('edit-meaning', meaningId, text)"
          @remove="meaningId => emit('remove-meaning', meaningId)"
        />
      </UCard>
    </section>
  </div>
</template>
