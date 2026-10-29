import type { ChoiceOption, ExerciseAnswer } from '~/models/practice'

/** What a question answered with an option needs from it. */
interface OptionQuestion {
  id: number
  answered: boolean
  answer: ExerciseAnswer | null
  options: ChoiceOption[]
}

// Where the shortcuts never apply: typing, a dialog (the item detail), or an
// open menu or select list (the sidebar's), whose keys are their own.
const OWN_KEYS = 'input, textarea, select, [contenteditable], [role="dialog"], [role="menu"], [role="listbox"], [role="combobox"]'

/**
 * How a question answered with an option is played, shared by the choice
 * card and the sentence players: pick an option (click or keys 1–N), skip
 * (S or Escape; a miss), and "next" (Enter) once answered. It measures the
 * time to answer and calls `answer` / `next`; the session page talks to the API.
 */
export function useOptionPlayer(
  question: () => OptionQuestion,
  busy: () => boolean,
  answer: (answer: ExerciseAnswer, responseMs: number) => void,
  next: () => void,
) {
  const shownAt = ref(0)
  const picked = ref<number | null>(null)

  watch(() => question().id, () => {
    shownAt.value = performance.now()
    const given = question().answer
    picked.value = given?.type === 'option' ? given.option : null
  }, { immediate: true })

  function elapsed() {
    return Math.round(performance.now() - shownAt.value)
  }

  function pick(option: number) {
    if (busy() || question().answered) return
    picked.value = option
    answer({ type: 'option', option }, elapsed())
  }

  function skip() {
    if (busy() || question().answered) return
    answer({ type: 'skip' }, elapsed())
  }

  const skipped = computed(() => question().answer?.type === 'skip')

  function onKey(event: KeyboardEvent) {
    if (event.defaultPrevented || event.repeat || event.ctrlKey || event.metaKey || event.altKey) return
    const target = event.target instanceof Element ? event.target : null
    if (target?.closest(OWN_KEYS)) return
    if (question().answered) {
      // Enter on a focused control ("Terminar", a link, a detail button) is that
      // control's; it means "next" only from the page itself or an option.
      const free = !target || target === document.body || target.closest('[data-option-shortcuts]')
      if (event.key === 'Enter' && free) {
        event.preventDefault()
        next()
      }
      return
    }
    if (event.key === 'Escape' || event.key.toLowerCase() === 's') {
      skip()
      return
    }
    const option = Number(event.key) - 1
    if (Number.isInteger(option) && option >= 0 && option < question().options.length) pick(option)
  }

  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

  return { picked, pick, skip, skipped }
}
