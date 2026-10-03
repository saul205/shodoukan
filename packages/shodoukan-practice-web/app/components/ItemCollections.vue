<script setup lang="ts">
import type { ItemKind } from '~/models/practice'

// The collections (tags) a library item is in, with adding and removing.
const props = defineProps<{ kind: ItemKind; itemId: number }>()

const { all, mine, busy, load, add, remove } = useItemCollections(() => props.kind, () => props.itemId)

watch(() => [props.kind, props.itemId], load, { immediate: true })

const available = computed(() => {
  const inside = new Set(mine.value.map(c => c.id))
  return (all.value ?? []).filter(c => !inside.has(c.id)).map(c => ({ label: c.name, value: c }))
})
</script>

<template>
  <div class="space-y-3">
    <div v-if="mine.length" class="flex flex-wrap gap-2">
      <UBadge
        v-for="collection in mine"
        :key="collection.id"
        color="primary"
        variant="soft"
        class="gap-1"
      >
        <NuxtLink :to="`/collections/${kind}/${collection.id}`" class="hover:underline">{{ collection.name }}</NuxtLink>
        <UButton
          icon="i-lucide-x"
          color="primary"
          variant="link"
          size="xs"
          class="p-0"
          :aria-label="`Quitar de ${collection.name}`"
          :disabled="busy"
          @click="remove(collection)"
        />
      </UBadge>
    </div>
    <p v-else class="text-sm text-muted">No está en ninguna colección.</p>

    <USelectMenu
      v-if="available.length"
      :items="available"
      value-key="value"
      :model-value="undefined"
      placeholder="Añadir a una colección…"
      icon="i-lucide-folder-plus"
      class="w-full"
      :disabled="busy"
      @update:model-value="collection => collection && add(collection)"
    />
    <p v-else-if="all && !all.length" class="text-sm text-muted">
      Aún no tienes colecciones. <ULink to="/collections" class="text-primary">Crea una</ULink>.
    </p>
  </div>
</template>
