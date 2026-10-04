<script setup lang="ts">
import type { SelectMenuProps } from '@nuxt/ui'
import type { Collection } from '~/models/practice'

// The collection picker behind every "add to a collection" icon: a searchable
// menu where typing a new name offers to create it. It only shows and emits;
// the caller does the requests (see `useItemCollections`).
//
// - Library mode (default): only the collections the item isn't in, to add it.
//   The page already shows the ones it's in, with their remove buttons.
// - `showSelected` (dictionary): every collection, ticked where the item is,
//   so it can also be taken out; the card has nowhere else to show that.
const props = withDefaults(defineProps<{
  /** The user's collections of this kind; null while loading. */
  collections: Collection[] | null
  /** The ones the item is in. */
  selected: Collection[]
  showSelected?: boolean
  tooltip?: string
  /**
   * Look like a `UButton` of this color, to sit beside one. A select's own
   * `color` only tints the focus ring, so the colors are applied as classes.
   */
  color?: 'neutral' | 'primary' | 'success'
  /** `solid` is only for primary and success; selects have no solid variant. */
  variant?: 'solid' | 'soft' | 'outline' | 'ghost'
  disabled?: boolean
}>(), { showSelected: false, tooltip: 'Añadir a una colección', color: 'neutral', variant: 'ghost' })

// The root is UTooltip, which renders no element: attributes go to the menu.
defineOptions({ inheritAttrs: false })

const emit = defineEmits<{
  open: []
  add: [collection: Collection]
  remove: [collection: Collection]
  create: [name: string]
}>()

const selectedIds = computed(() => props.selected.map(c => c.id))

const items = computed(() => {
  const all = props.collections ?? []
  const shown = props.showSelected ? all : all.filter(c => !selectedIds.value.includes(c.id))
  return shown.map(c => ({ label: c.name, value: c.id }))
})

const byId = (id: number) => props.collections?.find(c => c.id === id)

// Library mode: one pick at a time, nothing stays selected.
function picked(id: number | undefined) {
  const collection = id === undefined ? undefined : byId(id)
  if (collection) emit('add', collection)
}

// Dictionary mode: the menu reports the whole new selection; emit the change.
function changed(ids: number[]) {
  for (const id of ids.filter(id => !selectedIds.value.includes(id))) {
    const collection = byId(id)
    if (collection) emit('add', collection)
  }
  for (const collection of props.selected.filter(c => !ids.includes(c.id))) emit('remove', collection)
}

// UButton's classes for these colors (from its theme); written out in full so
// Tailwind sees them.
const BUTTON_COLORS = {
  primary: {
    solid: 'text-inverted bg-primary hover:bg-primary/75 disabled:bg-primary',
    soft: 'text-primary bg-primary/10 hover:bg-primary/15 disabled:bg-primary/10',
  },
  success: {
    solid: 'text-inverted bg-success hover:bg-success/75 disabled:bg-success',
    soft: 'text-success bg-success/10 hover:bg-success/15 disabled:bg-success/10',
  },
} as const

const look = computed<{ variant: SelectMenuProps['variant']; base: string }>(() => {
  if (props.color === 'neutral' || (props.variant !== 'solid' && props.variant !== 'soft'))
    return { variant: props.variant === 'solid' ? 'outline' : props.variant, base: '' }
  return { variant: 'none', base: BUTTON_COLORS[props.color][props.variant] }
})

// A square icon button like UButton's (the select puts its icon at the start,
// absolutely, and pads for it).
const ui = computed(() => ({
  base: `p-1.5 ${look.value.base}`,
  leading: 'static',
  leadingIcon: look.value.base ? 'text-current' : '',
  content: 'min-w-56',
}))

const emptyText = computed(() => {
  if (props.collections === null) return 'Cargando…'
  return props.collections.length ? 'Escribe un nombre para crear una colección' : 'Escribe un nombre para crear tu primera colección'
})
</script>

<template>
  <UTooltip :text="tooltip">
    <USelectMenu
      v-if="showSelected"
      multiple
      :items="items"
      value-key="value"
      :model-value="selectedIds"
      v-bind="$attrs"
      icon="i-lucide-folder-plus"
      trailing-icon=""
      color="neutral"
      :variant="look.variant"
      size="sm"
      :aria-label="tooltip"
      :disabled="disabled"
      :content="{ align: 'end' }"
      :ui="ui"
      :search-input="{ placeholder: 'Buscar o crear una colección…' }"
      create-item
      @update:open="isOpen => isOpen && emit('open')"
      @update:model-value="changed"
      @create="name => emit('create', name)"
    >
      <template #default><span class="sr-only">{{ tooltip }}</span></template>
      <template #create-item-label="{ item }">Crear «{{ item }}»</template>
      <template #empty>{{ emptyText }}</template>
    </USelectMenu>
    <USelectMenu
      v-else
      :items="items"
      value-key="value"
      :model-value="undefined"
      v-bind="$attrs"
      icon="i-lucide-folder-plus"
      trailing-icon=""
      color="neutral"
      :variant="look.variant"
      size="sm"
      :aria-label="tooltip"
      :disabled="disabled"
      :content="{ align: 'end' }"
      :ui="ui"
      :search-input="{ placeholder: 'Buscar o crear una colección…' }"
      create-item
      @update:open="isOpen => isOpen && emit('open')"
      @update:model-value="picked"
      @create="name => emit('create', name)"
    >
      <template #default><span class="sr-only">{{ tooltip }}</span></template>
      <template #create-item-label="{ item }">Crear «{{ item }}»</template>
      <template #empty>{{ emptyText }}</template>
    </USelectMenu>
  </UTooltip>
</template>
