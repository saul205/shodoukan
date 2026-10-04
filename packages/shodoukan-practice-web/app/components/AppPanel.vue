<script setup lang="ts">
// The frame of every screen: a navbar with the sidebar toggle and a title,
// and a scrollable body with the content at a readable width.
defineProps<{ title: string; id?: string }>()
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
      <UContainer class="max-w-6xl px-0 sm:px-0 lg:px-0">
        <slot />
      </UContainer>
    </template>
  </UDashboardPanel>
</template>
