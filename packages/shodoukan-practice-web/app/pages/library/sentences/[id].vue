<script setup lang="ts">
import ConfirmModal from '~/components/ConfirmModal.vue'
import type { Morpheme, PracticeSentence, SentenceProposal, SentenceWord } from '~/models/practice'
import {
  addSentenceWord,
  analyzeSentences,
  correctSentenceWord,
  getSentence,
  linkSentenceWord,
  removeSentence,
  removeSentenceWord,
  rewriteSentence,
  setSentenceActive,
  setSentenceNotes,
} from '~/services/sentences'
import { sentenceTranslation } from '~/utils/sentences'

// One sentence of the library and its words. Each word is a gap the
// exercises can ask (its span), linked to a word of the library (what it
// is), with what the analyzer says of it (its dictionary form and reading,
// which can be corrected). A word is marked by clicking it in the sentence;
// the words of the library it uses that aren't linked yet are suggested.
// A dictionary sentence can't be rewritten, only hidden.

const route = useRoute()
const api = useApi()
const notify = useNotify()
const overlay = useOverlay()
const { glossCode } = useMeaningLang()

const id = computed(() => Number(route.params.id))
const { item: sentence, status, saving, save } = useEditableItem<PracticeSentence>(
  () => `sentence-${id.value}`,
  () => getSentence(api, id.value),
)

// Its morphemes (to click a word) and the library words it uses, analyzed
// again whenever its text changes.
const analysis = ref<SentenceProposal | null>(null)
watch(() => sentence.value?.text, async (text) => {
  if (!text) return
  try {
    analysis.value = (await analyzeSentences(api, [text]))[0] ?? null
  }
  catch {
    analysis.value = null
  }
}, { immediate: true })

const spans = computed(() =>
  (sentence.value?.words ?? [])
    .filter(w => w.start !== null && w.end !== null)
    .map(w => ({ start: w.start as number, end: w.end as number, tone: w.entry_id ? 'primary' as const : 'neutral' as const })),
)

function covers(word: SentenceWord, start: number, end: number): boolean {
  return word.start !== null && word.end !== null && word.start < end && start < word.end
}

function wordAt(morpheme: Morpheme): SentenceWord | undefined {
  return sentence.value?.words.find(w => covers(w, morpheme.start, morpheme.end))
}

/** The library words it uses that no word of it marks yet. */
const suggestions = computed(() =>
  (analysis.value?.words ?? []).filter(p => !(sentence.value?.words ?? []).some(w => covers(w, p.start, p.end))),
)

function surface(word: SentenceWord): string {
  return word.start !== null && word.end !== null && sentence.value
    ? sentence.value.text.slice(word.start, word.end)
    : ''
}

function markMorpheme(morpheme: Morpheme) {
  if (wordAt(morpheme)) return
  void save(() => addSentenceWord(api, id.value, morpheme.start, morpheme.end))
}

// Rewriting an own sentence.
const editing = ref(false)
const japanese = ref('')
const translation = ref('')

function startEditing() {
  if (!sentence.value) return
  japanese.value = sentence.value.text
  translation.value = sentenceTranslation(sentence.value, glossCode.value)
  editing.value = true
}

async function rewrite() {
  const text = japanese.value.trim()
  if (!text) return
  const saved = await save(() => rewriteSentence(api, id.value, text, translation.value.trim() || null, glossCode.value))
  if (saved) editing.value = false
}

// Correcting a word's dictionary form and reading.
const correcting = ref<number | null>(null)
const lemma = ref('')
const reading = ref('')

function startCorrecting(word: SentenceWord) {
  correcting.value = word.id
  lemma.value = word.lemma ?? surface(word)
  reading.value = word.reading ?? ''
}

async function correct(word: SentenceWord) {
  const saved = await save(() => correctSentenceWord(api, id.value, word.id, lemma.value.trim(), reading.value.trim()))
  if (saved) correcting.value = null
}

async function remove() {
  const confirmed = await overlay.create(ConfirmModal).open({
    title: '¿Eliminar la frase?',
    description: 'Se quita de tu librería, también de las palabras que la usan.',
    confirmLabel: 'Eliminar',
  }).result
  if (!confirmed) return
  try {
    await removeSentence(api, id.value)
    notify.success('Frase eliminada')
    await navigateTo('/library/sentences')
  }
  catch (failure) {
    notify.failure(failure, 'No se ha podido eliminar')
  }
}
</script>

<template>
  <AppPanel title="Frase">
    <template #leading>
      <UButton icon="i-lucide-arrow-left" color="neutral" variant="ghost" to="/library/sentences" aria-label="Volver a las frases" />
    </template>

    <div v-if="status === 'pending' && !sentence" class="space-y-4">
      <USkeleton class="h-12 w-full" />
      <USkeleton v-for="i in 3" :key="i" class="h-16 w-full" />
    </div>

    <UEmpty
      v-else-if="!sentence"
      icon="i-lucide-search-x"
      title="Esta frase no está en tu librería"
      :actions="[{ label: 'Volver a las frases', to: '/library/sentences', icon: 'i-lucide-arrow-left' }]"
    />

    <div v-else class="grid gap-8 lg:grid-cols-3">
      <div class="space-y-6 lg:col-span-2">
        <UCard>
          <form v-if="editing" class="space-y-2" data-testid="rewrite-form" @submit.prevent="rewrite" @keydown.esc="editing = false">
            <UInput v-model="japanese" class="w-full font-japanese" :maxlength="500" :disabled="saving" autofocus />
            <UInput v-model="translation" placeholder="Traducción (opcional)" class="w-full" :maxlength="500" :disabled="saving" />
            <div class="flex gap-2">
              <UButton type="submit" label="Guardar" size="sm" :loading="saving" :disabled="!japanese.trim()" />
              <UButton label="Cancelar" size="sm" color="neutral" variant="ghost" @click="editing = false" />
            </div>
          </form>
          <div v-else class="flex items-start gap-3">
            <div class="flex-1 space-y-1">
              <p class="text-xl text-default" data-testid="sentence-text">
                <SentenceText :text="sentence.text" :spans="spans" />
              </p>
              <p v-if="sentenceTranslation(sentence, glossCode)" class="text-muted">
                {{ sentenceTranslation(sentence, glossCode) }}
              </p>
            </div>
            <UButton
              v-if="sentence.origin === 'added'"
              icon="i-lucide-pencil"
              color="neutral"
              variant="ghost"
              size="sm"
              aria-label="Reescribir la frase"
              data-testid="rewrite"
              @click="startEditing"
            />
          </div>
        </UCard>

        <section v-if="analysis" class="space-y-2">
          <h2 class="text-sm font-semibold text-highlighted">Marcar una palabra</h2>
          <p class="text-sm text-muted">Pulsa una palabra de la frase para convertirla en un hueco.</p>
          <div class="flex flex-wrap gap-1" data-testid="morphemes">
            <UButton
              v-for="m in analysis.morphemes"
              :key="m.start"
              :label="m.surface"
              size="sm"
              class="font-japanese"
              :color="wordAt(m) ? 'primary' : 'neutral'"
              :variant="wordAt(m) ? 'soft' : 'ghost'"
              :disabled="saving"
              @click="markMorpheme(m)"
            />
          </div>
        </section>

        <section v-if="suggestions.length" class="space-y-2" data-testid="suggestions">
          <h2 class="text-sm font-semibold text-highlighted">Palabras de tu librería en esta frase</h2>
          <div v-for="s in suggestions" :key="s.start" class="flex items-center gap-3">
            <span class="font-japanese text-default">{{ sentence.text.slice(s.start, s.end) }}</span>
            <span class="text-sm text-muted">{{ s.form }}</span>
            <UBadge v-if="!s.certain" color="warning" variant="soft" label="Solo en kana" />
            <UButton
              label="Enlazar"
              size="xs"
              variant="soft"
              :disabled="saving"
              @click="save(() => addSentenceWord(api, id, s.start, s.end, s.entry_ids[0] ?? null))"
            />
          </div>
        </section>

        <section class="space-y-3">
          <h2 class="text-sm font-semibold text-highlighted">Sus palabras</h2>
          <p v-if="!sentence.words.length" class="text-sm text-muted">Aún no tiene ninguna: márcalas arriba.</p>
          <UCard v-for="word in sentence.words" :key="word.id" :ui="{ body: 'space-y-3' }" data-testid="sentence-word">
            <div class="flex flex-wrap items-center gap-3">
              <span class="font-japanese text-lg text-default">{{ surface(word) || '—' }}</span>
              <UBadge v-if="word.start === null" color="warning" variant="soft" label="Sin hueco: no se pregunta" />
              <span v-if="word.lemma" class="text-sm text-muted">
                {{ word.lemma }} · {{ word.reading }}
                <template v-if="word.inflection?.endings.length"> · {{ word.inflection.endings.join('+') }}</template>
              </span>
              <div class="ms-auto flex gap-1">
                <UButton
                  v-if="word.start !== null"
                  icon="i-lucide-spell-check"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  aria-label="Corregir forma y lectura"
                  :disabled="saving"
                  @click="startCorrecting(word)"
                />
                <UButton
                  icon="i-lucide-trash-2"
                  color="error"
                  variant="ghost"
                  size="xs"
                  aria-label="Quitar esta palabra"
                  :disabled="saving"
                  data-testid="remove-word"
                  @click="save(() => removeSentenceWord(api, id, word.id))"
                />
              </div>
            </div>
            <form v-if="correcting === word.id" class="flex flex-wrap gap-2" @submit.prevent="correct(word)">
              <UInput v-model="lemma" placeholder="Forma de diccionario" class="font-japanese" />
              <UInput v-model="reading" placeholder="Lectura en kana" class="font-japanese" />
              <UButton type="submit" label="Guardar" size="sm" :loading="saving" :disabled="!lemma.trim() || !reading.trim()" />
              <UButton label="Cancelar" size="sm" color="neutral" variant="ghost" @click="correcting = null" />
            </form>
            <LibraryWordSelect
              :model-value="word.entry_id"
              :disabled="saving"
              @update:model-value="entryId => save(() => linkSentenceWord(api, id, word.id, entryId))"
            />
          </UCard>
        </section>
      </div>

      <aside class="space-y-6">
        <UCard :ui="{ body: 'space-y-3' }">
          <USwitch
            :model-value="sentence.is_active"
            :disabled="saving"
            label="Se practica"
            description="Si la ocultas, no sale en los ejercicios."
            @update:model-value="active => save(() => setSentenceActive(api, id, active))"
          />
          <p class="text-sm text-muted">
            {{ sentence.origin === 'added' ? 'Frase propia.' : 'Del diccionario: no se puede reescribir.' }}
          </p>
        </UCard>
        <NotesEditor
          :notes="sentence.notes"
          label="Nota"
          :saving="saving"
          @save="notes => save(() => setSentenceNotes(api, id, notes))"
        />
        <UButton
          v-if="sentence.origin === 'added'"
          label="Eliminar la frase"
          icon="i-lucide-trash-2"
          color="error"
          variant="soft"
          data-testid="remove-sentence"
          @click="remove"
        />
      </aside>
    </div>
  </AppPanel>
</template>
