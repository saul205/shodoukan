<script setup lang="ts">
import type { Collection, ItemKind } from '~/models/practice'

// The folder half of the dictionary's import button: a `CollectionPicker`
// that shows the collections the item is in (ticked, so it can be taken out)
// and imports it first when it isn't in the library yet. For that it emits
// `import` with the collection, and the page imports the item into it in one
// request. The collections load when the menu opens, not once per result.
const props = defineProps<{
  kind: ItemKind
  /** The library copy's id; undefined while the item isn't imported. */
  practiceId?: number
  /** The item is being imported or removed. */
  loading?: boolean
  /** Match the import button next to it (soft in a card's corner). */
  iconOnly?: boolean
}>()

const emit = defineEmits<{ import: [into: Collection] }>()

const { all, mine, busy, load, add, remove, create } = useItemCollections(() => props.kind, () => props.practiceId)

const opened = ref(false)
const imported = computed(() => props.practiceId !== undefined)

function open() {
  opened.value = true
  load()
}
// Once imported, show it ticked in the collection it went into.
watch(() => props.practiceId, () => {
  if (opened.value) load()
})

function addTo(collection: Collection) {
  if (imported.value) add(collection)
  else emit('import', collection)
}

async function createAndAdd(name: string) {
  const created = await create(name)
  if (created) addTo(created)
}
</script>

<template>
  <CollectionPicker
    show-selected
    :collections="all"
    :selected="mine"
    :variant="iconOnly ? 'soft' : 'outline'"
    :disabled="busy || loading"
    @open="open"
    @add="addTo"
    @remove="remove"
    @create="createAndAdd"
  />
</template>
