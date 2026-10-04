<script setup lang="ts">
import type { DropdownMenuItem, NavigationMenuItem } from '@nuxt/ui'

const auth = useAuth()
const { lang, options: languages } = useMeaningLang()

const items: NavigationMenuItem[] = [
  { label: 'Diccionario', icon: 'i-lucide-book-open', to: '/dictionary' },
  { label: 'Mi librería', icon: 'i-lucide-library-big', to: '/library' },
  { label: 'Mis colecciones', icon: 'i-lucide-folders', to: '/collections' },
]

const userMenu = computed<DropdownMenuItem[][]>(() => [
  [{ label: auth.username.value || 'Mi cuenta', type: 'label' }],
  [{ label: 'Cerrar sesión', icon: 'i-lucide-log-out', onSelect: () => auth.logout() }],
])
</script>

<template>
  <UDashboardGroup storage="local" storage-key="practice-sidebar">
    <UDashboardSidebar collapsible :ui="{ footer: 'flex-col items-stretch gap-2' }">
      <template #header="{ collapsed }">
        <NuxtLink to="/" class="flex items-center gap-2 font-semibold text-highlighted">
          <UIcon name="i-lucide-graduation-cap" class="size-6 shrink-0 text-primary" />
          <span v-if="!collapsed">Shodoukan <span class="font-normal text-muted">· práctica</span></span>
        </NuxtLink>
      </template>

      <template #default="{ collapsed }">
        <UNavigationMenu :collapsed="collapsed" :items="items" orientation="vertical" />
      </template>

      <template #footer="{ collapsed }">
        <UFormField v-if="!collapsed" label="Idioma de los significados" size="xs">
          <USelect v-model="lang" :items="languages" size="sm" class="w-full" />
        </UFormField>
        <UDropdownMenu :items="userMenu" :content="{ align: 'start' }">
          <UButton
            :label="collapsed ? undefined : (auth.username.value || 'Mi cuenta')"
            icon="i-lucide-circle-user-round"
            color="neutral"
            variant="ghost"
            block
            :square="collapsed"
            class="data-[state=open]:bg-elevated"
          />
        </UDropdownMenu>
      </template>
    </UDashboardSidebar>

    <slot />
  </UDashboardGroup>
</template>
