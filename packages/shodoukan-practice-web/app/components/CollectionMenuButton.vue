<script setup lang="ts">
import CollectionFormModal from '~/components/CollectionFormModal.vue'
import type { Collection, ItemKind } from '~/models/practice'

// The folder half of the dictionary's import button: a popover with the user's
// collections, ticked where the item is. Ticking one for an item that isn't
// imported yet emits `import` so the page imports it into that collection in
// one request; for an imported item (`practiceId`) it adds or removes it here.
// The collections load when the popover opens, not once per result.
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

const overlay = useOverlay()
const { all, busy, has, load, add, remove } = useItemCollections(() => props.kind, () => props.practiceId)

const open = ref(false)
const imported = computed(() => props.practiceId !== undefined)
const disabled = computed(() => busy.value || props.loading)

watch(open, (isOpen) => {
  if (isOpen) load()
})
// Once imported, show it ticked in the collection it went into.
watch(() => props.practiceId, () => {
  if (open.value) load()
})

function toggle(collection: Collection, checked: boolean | 'indeterminate') {
  if (!imported.value) emit('import', collection)
  else if (checked === true) add(collection)
  else remove(collection)
}

async function create() {
  open.value = false
  const saved: Collection | null = await overlay.create(CollectionFormModal).open({ kind: props.kind }).result
  if (!saved) return
  if (imported.value) await add(saved)
  else emit('import', saved)
}
</script>

<template>
  <UPopover v-model:open="open" :content="{ align: 'end' }">
    <UTooltip text="Añadir a una colección" :disabled="open">
      <UButton
        icon="i-lucide-folder-plus"
        aria-label="Añadir a una colección"
        :color="imported ? 'success' : 'primary'"
        :variant="imported || iconOnly ? 'soft' : 'solid'"
        size="sm"
      />
    </UTooltip>

    <template #content>
      <div class="w-64 space-y-1 p-2">
        <p class="px-2 py-1 text-xs font-medium text-muted">Añadir a una colección</p>
        <p v-if="all === null" class="px-2 py-1 text-sm text-muted">Cargando…</p>
        <template v-else>
          <UCheckbox
            v-for="collection in all"
            :key="collection.id"
            :model-value="has(collection)"
            :label="collection.name"
            :disabled="disabled"
            class="rounded-md px-2 py-1.5 hover:bg-elevated"
            @update:model-value="checked => toggle(collection, checked)"
          />
          <p v-if="!all.length" class="px-2 py-1 text-sm text-muted">Aún no tienes colecciones.</p>
        </template>
        <USeparator class="my-1" />
        <UButton
          label="Nueva colección"
          icon="i-lucide-plus"
          color="neutral"
          variant="ghost"
          size="sm"
          block
          class="justify-start"
          :disabled="disabled"
          @click="create"
        />
      </div>
    </template>
  </UPopover>
</template>
