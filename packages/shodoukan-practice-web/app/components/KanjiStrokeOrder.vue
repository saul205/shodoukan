<script setup lang="ts">
import { KanjiStrokeAnimator, KanjiStrokeGrid } from 'shodoukan-ui'
import { getDictionaryKanjiStrokes } from '~/services/dictionary'
import { apiStatus } from '~/utils/api-error'

// A kanji's stroke order (KanjiVG, from the practice API): the animation and
// one frame per stroke, fetched once for both. Kanji without a drawing (404)
// show "not available" instead. KanjiVG is credited on /about, not here.

const props = withDefaults(defineProps<{
  literal: string
  /** Size of the animation, in px. */
  size?: number
  /** Smallest width of a stroke frame (CSS length). */
  cellSize?: string
}>(), { size: 160, cellSize: '6rem' })

const api = useApi()

const { data, status } = useAsyncData(
  () => `kanji-strokes-${props.literal}`,
  async () => {
    try {
      return await getDictionaryKanjiStrokes(api, props.literal)
    }
    catch (error) {
      if (apiStatus(error) === 404) return null
      throw error
    }
  },
  { watch: [() => props.literal] },
)

const strokes = computed(() => data.value?.strokes ?? null)
</script>

<template>
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start">
    <KanjiStrokeAnimator
      :key="literal"
      :strokes="strokes"
      :size="size"
      play-label="Reproducir"
      playing-label="Reproduciendo…"
    />
    <div class="flex-1">
      <KanjiStrokeGrid
        :strokes="strokes"
        :loading="status === 'pending'"
        :cell-size="cellSize"
        loading-label="Cargando el orden de trazos…"
        unavailable-label="Orden de trazos no disponible."
      />
    </div>
  </div>
</template>
