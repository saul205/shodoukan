// The size of an element's box, followed as it changes, and as the element
// comes and goes (a `v-if`). Used to fit a square drawing pad into the room a
// box leaves for it: measure the box, not its content.
export function useMeasuredBox(box: Ref<HTMLElement | null>) {
  const room = ref({ width: 0, height: 0 })
  if (typeof ResizeObserver === 'undefined') return room
  const observer = new ResizeObserver(([entry]) => {
    if (entry) room.value = { width: entry.contentRect.width, height: entry.contentRect.height }
  })
  watch(box, (element, previous) => {
    if (previous) observer.unobserve(previous)
    if (element) observer.observe(element)
  }, { immediate: true, flush: 'post' })
  onBeforeUnmount(() => observer.disconnect())
  return room
}
