<script setup lang="ts">
// The frame of every screen: a navbar with the sidebar toggle and a title,
// and a scrollable body with the content at a readable width. `fill` stretches
// the content to the body's height (a full-screen view such as a session).
defineProps<{ title: string; id?: string; fill?: boolean }>()
</script>

<template>
  <UDashboardPanel :id="id">
    <template #header>
      <UDashboardNavbar :title="title">
        <template #leading>
          <UDashboardSidebarCollapse />
          <slot name="leading" />
        </template>
        <template #right>
          <slot name="actions" />
        </template>
      </UDashboardNavbar>
      <slot name="toolbar" />
    </template>

    <template #body>
      <UContainer class="max-w-6xl px-0 sm:px-0 lg:px-0" :class="{ 'flex min-h-0 flex-1 flex-col': fill }">
        <slot />
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
