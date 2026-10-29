<script setup lang="ts">
import type { PracticeEntry } from '~/models/practice'
import { getLibraryEntry, listLibraryEntries } from '~/services/library'
import { entryHeadword, entryMeanings, entryReading } from '~/utils/practice-text'

// Pick a word of the library, searching it by spelling, reading or meaning:
// what a sentence's word is linked to. `null` is no word.

const props = defineProps<{ modelValue: number | null; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [entryId: number | null] }>()

const api = useApi()
const { glossCode } = useMeaningLang()

interface Option { label: string; description: string; value: number }

const searchTerm = ref('')
const options = ref<Option[]>([])
const loading = ref(false)

function option(entry: PracticeEntry): Option {
  const reading = entryReading(entry)
  return {
    label: reading ? `${entryHeadword(entry)}（${reading}）` : entryHeadword(entry),
    description: entryMeanings(entry, glossCode.value).slice(0, 3).join('; '),
    value: entry.id,
  }
}

async function search(text: string) {
  loading.value = true
  try {
    const page = await listLibraryEntries(api, {
      q: text || undefined,
      meaning_lang: text ? glossCode.value : undefined,
      limit: 20,
    })
    const found = page.items.map(option)
    // The chosen word stays among the options, so its label shows.
    const chosen = options.value.find(o => o.value === props.modelValue)
    options.value = chosen && !found.some(o => o.value === chosen.value) ? [chosen, ...found] : found
  }
  catch {
    options.value = []
  }
  finally {
    loading.value = false
  }
}

watch(searchTerm, text => search(text.trim()))

// The chosen word's label, when it isn't among the options yet.
watch(() => props.modelValue, async (id) => {
  if (id === null || options.value.some(o => o.value === id)) return
  try {
    options.value = [option(await getLibraryEntry(api, id)), ...options.value]
  }
  catch {
    // A word no longer in the library: shown by its id only.
  }
}, { immediate: true })

onMounted(() => search(''))
</script>

<template>
  <USelectMenu
    v-model:search-term="searchTerm"
    :model-value="modelValue ?? undefined"
    :items="options"
    value-key="value"
    :loading="loading"
    :disabled="disabled"
    ignore-filter
    placeholder="Elige una palabra"
    :search-input="{ placeholder: 'Busca en tu librería…' }"
    class="w-full"
    @update:model-value="(value: number | undefined) => emit('update:modelValue', value ?? null)"
  />
</template>
