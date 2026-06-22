<script setup lang="ts">
const route = useRoute()

const query = ref((route.query.q as string) ?? '')
const lang = ref((route.query.lang as string) ?? 'en')

watch(
  () => route.query,
  (q) => {
    query.value = (q.q as string) ?? ''
    lang.value = (q.lang as string) ?? 'en'
  },
)

function doSearch() {
  navigateTo({ path: '/', query: { q: query.value, lang: lang.value } })
}
</script>

<template>
  <div class="min-h-screen bg-zinc-900 text-zinc-100">
    <header class="sticky top-0 z-50 bg-zinc-900">
      <NavBar />
      <div class="border-b border-zinc-800 px-6 py-3">
        <div class="mx-auto max-w-3xl">
          <SearchBar v-model="query" v-model:lang="lang" @search="doSearch" />
        </div>
      </div>
    </header>
    <slot />
  </div>
</template>
