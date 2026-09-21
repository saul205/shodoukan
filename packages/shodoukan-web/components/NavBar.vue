<script setup lang="ts">
const route = useRoute()
const lastSearch = useLastSearch()

const isDictionary = computed(() =>
  route.path === '/' || route.path.startsWith('/kanji/') || route.path.startsWith('/entry/'),
)

const dictionaryTo = computed(() =>
  lastSearch.value.q
    ? { path: '/', query: { q: lastSearch.value.q, lang: lastSearch.value.lang } }
    : '/',
)
</script>

<template>
  <nav class="flex items-center gap-6 border-b border-zinc-800 bg-zinc-900 px-6 py-3">
    <NuxtLink
      to="/"
      class="mr-4 font-semibold tracking-wide text-zinc-100 hover:text-white"
    >
      Shodoukan
    </NuxtLink>

    <NuxtLink
      :to="dictionaryTo"
      class="text-sm transition"
      :class="isDictionary ? 'text-white' : 'text-zinc-400 hover:text-zinc-200'"
    >
      Dictionary
    </NuxtLink>
    <NuxtLink
      to="/about"
      class="text-sm transition"
      :class="route.path === '/about' ? 'text-white' : 'text-zinc-400 hover:text-zinc-200'"
    >
      About
    </NuxtLink>
    <NuxtLink
      to="/sources"
      class="text-sm transition"
      :class="route.path === '/sources' ? 'text-white' : 'text-zinc-400 hover:text-zinc-200'"
    >
      Sources
    </NuxtLink>
  </nav>
</template>
