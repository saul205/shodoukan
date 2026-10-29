<script setup lang="ts">
import type { Morpheme, SentenceDraft, SentenceProposal } from '~/models/practice'
import { addSentences, analyzeSentences } from '~/services/sentences'

// Add sentences of the user's own in bulk. They're pasted one per line (a
// translation after a tab, optional), analyzed on the server, and reviewed
// in a list before anything is stored: each row shows the words of the
// library it found (a kana-only match, which may be another word, in another
// colour and left out until confirmed) and a summary. A row opens to check
// its words, pick the right word when several fit, or mark another word by
// clicking it. "Guardar todas" stores them at once.

const MAX_SENTENCES = 200

const api = useApi()
const notify = useNotify()
const { glossCode } = useMeaningLang()

interface Word {
  start: number
  end: number
  /** The library words it may be; several when they share the form. */
  entryIds: number[]
  entryId: number | null
  included: boolean
  certain: boolean
}

interface Row {
  text: string
  translation: string | null
  morphemes: Morpheme[]
  words: Word[]
}

const pasted = ref('')
const rows = ref<Row[] | null>(null)
const open = ref<number | null>(null)
const analyzing = ref(false)
const saving = ref(false)

const lines = computed(() =>
  pasted.value.split('\n').map(l => l.trim()).filter(Boolean).map((line) => {
    const [text = '', ...rest] = line.split('\t')
    return { text: text.trim(), translation: rest.join(' ').trim() || null }
  }).filter(l => l.text),
)

async function analyze() {
  if (!lines.value.length || lines.value.length > MAX_SENTENCES) return
  analyzing.value = true
  try {
    const proposals = await analyzeSentences(api, lines.value.map(l => l.text))
    rows.value = proposals.map((proposal, i) => row(proposal, lines.value[i]?.translation ?? null))
    open.value = null
  }
  catch (failure) {
    notify.failure(failure)
  }
  finally {
    analyzing.value = false
  }
}

function row(proposal: SentenceProposal, translation: string | null): Row {
  return {
    text: proposal.text,
    translation,
    morphemes: proposal.morphemes,
    words: proposal.words.map(w => ({
      start: w.start,
      end: w.end,
      entryIds: w.entry_ids,
      entryId: w.entry_ids.length === 1 || w.certain ? (w.entry_ids[0] ?? null) : null,
      included: w.certain,
      certain: w.certain,
    })),
  }
}

function summary(r: Row) {
  const linked = r.words.filter(w => w.included && w.entryId !== null).length
  const doubtful = r.words.filter(w => !w.included || w.entryId === null).length
  return { linked, doubtful }
}

function spans(r: Row) {
  return r.words.map(w => ({
    start: w.start,
    end: w.end,
    tone: w.included && w.entryId !== null ? 'primary' as const : 'warning' as const,
  }))
}

/** Mark or unmark a word by its morpheme (a word the analysis didn't find). */
function toggleMorpheme(r: Row, morpheme: Morpheme) {
  const at = r.words.findIndex(w => w.start <= morpheme.start && morpheme.end <= w.end)
  if (at >= 0) {
    r.words.splice(at, 1)
    return
  }
  r.words.push({ start: morpheme.start, end: morpheme.end, entryIds: [], entryId: null, included: true, certain: true })
  r.words.sort((a, b) => a.start - b.start)
}

function isMarked(r: Row, morpheme: Morpheme): boolean {
  return r.words.some(w => w.start <= morpheme.start && morpheme.end <= w.end)
}

const total = computed(() => rows.value?.length ?? 0)

async function saveAll() {
  if (!rows.value?.length) return
  const drafts: SentenceDraft[] = rows.value.map(r => ({
    japanese: r.text,
    translation: r.translation,
    lang: glossCode.value,
    words: r.words
      .filter(w => w.included)
      .map(w => ({ start: w.start, end: w.end, entry_id: w.entryId })),
  }))
  saving.value = true
  try {
    const saved = await addSentences(api, drafts)
    notify.success(`${saved.length} ${saved.length === 1 ? 'frase añadida' : 'frases añadidas'}`)
    await navigateTo('/library/sentences')
  }
  catch (failure) {
    notify.failure(failure)
  }
  finally {
    saving.value = false
  }
}
</script>

<template>
  <AppPanel title="Añadir frases">
    <template #leading>
      <UButton icon="i-lucide-arrow-left" color="neutral" variant="ghost" to="/library/sentences" aria-label="Volver a las frases" />
    </template>

    <div class="space-y-5">
      <template v-if="rows === null">
        <p class="text-sm text-muted">
          Pega tus frases, una por línea. Si quieres, añade su traducción detrás de un tabulador. Se analizan antes de
          guardarlas: podrás revisar qué palabras de tu librería usa cada una.
        </p>
        <UTextarea
          v-model="pasted"
          :rows="10"
          autoresize
          class="w-full font-japanese"
          placeholder="毎朝、駅まで歩いて行きます。	I walk to the station every morning."
          data-testid="pasted"
        />
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm" :class="lines.length > MAX_SENTENCES ? 'text-error' : 'text-muted'">
            {{ lines.length }} {{ lines.length === 1 ? 'frase' : 'frases' }}
            <template v-if="lines.length > MAX_SENTENCES">(como mucho {{ MAX_SENTENCES }} cada vez)</template>
          </p>
          <UButton
            label="Analizar"
            icon="i-lucide-scan-text"
            :loading="analyzing"
            :disabled="!lines.length || lines.length > MAX_SENTENCES"
            data-testid="analyze"
            @click="analyze"
          />
        </div>
      </template>

      <template v-else>
        <div class="flex flex-wrap items-center justify-between gap-3">
          <p class="text-sm text-muted">
            {{ total }} {{ total === 1 ? 'frase' : 'frases' }}. Subrayadas, las palabras de tu librería que se enlazarán;
            en naranja, las que hay que confirmar. Abre una frase para revisarla.
          </p>
          <div class="flex gap-2">
            <UButton label="Volver a editar" color="neutral" variant="ghost" @click="rows = null" />
            <UButton label="Guardar todas" icon="i-lucide-check" :loading="saving" data-testid="save-all" @click="saveAll" />
          </div>
        </div>

        <ul class="divide-y divide-default rounded-md border border-default">
          <li v-for="(r, i) in rows" :key="i" class="p-3" data-testid="review-row">
            <button type="button" class="flex w-full items-start gap-3 text-left" @click="open = open === i ? null : i">
              <span class="flex-1">
                <span class="block text-default"><SentenceText :text="r.text" :spans="spans(r)" /></span>
                <span v-if="r.translation" class="block text-sm text-muted">{{ r.translation }}</span>
              </span>
              <span class="flex shrink-0 gap-1">
                <UBadge v-if="summary(r).linked" color="primary" variant="soft" :label="`${summary(r).linked} enlazadas`" />
                <UBadge v-if="summary(r).doubtful" color="warning" variant="soft" :label="`${summary(r).doubtful} dudosas`" />
                <UBadge v-if="!r.words.length" color="neutral" variant="soft" label="Sin palabras" data-testid="no-words" />
              </span>
            </button>

            <div v-if="open === i" class="mt-3 space-y-3 border-t border-default pt-3" data-testid="review-editor">
              <div>
                <p class="mb-1 text-xs font-medium uppercase tracking-wide text-dimmed">Pulsa una palabra para marcarla</p>
                <div class="flex flex-wrap gap-1">
                  <UButton
                    v-for="m in r.morphemes"
                    :key="m.start"
                    :label="m.surface"
                    size="xs"
                    class="font-japanese"
                    :color="isMarked(r, m) ? 'primary' : 'neutral'"
                    :variant="isMarked(r, m) ? 'soft' : 'ghost'"
                    @click="toggleMorpheme(r, m)"
                  />
                </div>
              </div>
              <div v-for="(word, j) in r.words" :key="`${word.start}-${j}`" class="flex flex-wrap items-center gap-3">
                <UCheckbox v-model="word.included" :aria-label="`Incluir ${r.text.slice(word.start, word.end)}`" />
                <span class="w-24 font-japanese text-default">{{ r.text.slice(word.start, word.end) }}</span>
                <div class="min-w-56 flex-1">
                  <LibraryWordSelect v-model="word.entryId" />
                </div>
                <UBadge v-if="!word.certain" color="warning" variant="soft" label="Solo en kana: confírmala" />
              </div>
            </div>
          </li>
        </ul>
      </template>
    </div>
  </AppPanel>
</template>
