<template>
  <main class="mx-auto max-w-2xl px-6 py-16">
    <h1 class="mb-2 text-3xl font-bold text-zinc-100">
      About Shodoukan
    </h1>
    <p class="mb-10 text-zinc-400">
      Japanese-English dictionary platform built on JMDict and KANJIDIC2.
    </p>

    <section class="mb-10">
      <h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
        What it is
      </h2>
      <p class="text-zinc-300">
        Shodoukan is an open-source dictionary for looking up Japanese words, kanji readings,
        and multilingual glosses. It supports searches by kanji, kana, Hepburn romaji,
        or gloss in English, Spanish, French, and German.
      </p>
    </section>

    <section class="mb-10">
      <h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
        Repositories
      </h2>
      <div class="flex flex-col gap-2">
        <a
          href="https://github.com/saul205/shodoukan"
          target="_blank"
          rel="noopener"
          class="flex items-center gap-2 text-indigo-400 transition hover:text-indigo-300"
        >
          <span>saul205/shodoukan</span>
          <span class="text-xs text-zinc-500">— API + web interface</span>
        </a>
        <a
          href="https://github.com/saul205/shodoukan-db"
          target="_blank"
          rel="noopener"
          class="flex items-center gap-2 text-indigo-400 transition hover:text-indigo-300"
        >
          <span>saul205/shodoukan-db</span>
          <span class="text-xs text-zinc-500">— database pipeline (Rust)</span>
        </a>
      </div>
    </section>

    <section>
      <h2 class="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500">
        Tech stack
      </h2>
      <table class="w-full text-sm">
        <tbody class="divide-y divide-zinc-800">
          <tr v-for="row in stack" :key="row.layer" class="py-2">
            <td class="py-2 pr-6 text-zinc-500">
              {{ row.layer }}
            </td>
            <td class="py-2 text-zinc-300">
              {{ row.tech }}
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </main>
</template>

<script setup lang="ts">
definePageMeta({ layout: 'dictionary' })

const stack = [
  { layer: 'Data', tech: 'JMDict · KANJIDIC2' },
  { layer: 'DB pipeline', tech: 'Rust · SQLite' },
  { layer: 'Library', tech: 'Python · SQLAlchemy' },
  { layer: 'API', tech: 'FastAPI · Pydantic' },
  { layer: 'Frontend', tech: 'Nuxt 3 · Vue 3 · Tailwind CSS' },
]
</script>
