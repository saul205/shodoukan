// @vitest-environment nuxt
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, type VueWrapper } from '@vue/test-utils'
import { mockNuxtImport, mountSuspended } from '@nuxt/test-utils/runtime'
import { FetchError } from 'ofetch'
import { URadioGroup, USelectMenu } from '#components'
import DirectionsEditor from '../../app/components/DirectionsEditor.vue'
import ExerciseForm from '../../app/components/ExerciseForm.vue'
import type { Exercise } from '../../app/models/practice'
import { signedInAuth } from '../fakes'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))

mockNuxtImport('useAuth', () => signedInAuth)
mockNuxtImport('useApi', () => () => api)

const collection = (id: number, name: string) => ({ id, name, description: null, created_at: '', updated_at: '' })

const saved: Exercise = {
  id: 7,
  name: 'Verbos',
  description: null,
  item_kind: 'entries',
  collection_ids: [1],
  settings: {
    type: 'card.choice',
    directions: [{ prompt: ['writing'], answer: 'meaning' }],
    back_fields: ['reading'],
    option_count: 4,
    distractor_source: 'collection',
  },
  created_at: '',
  updated_at: '',
}

function respond(overrides: Record<string, unknown> = {}) {
  api.mockImplementation(async (url: string, options?: { method?: string }) => {
    if (url in overrides) {
      const value = overrides[url]
      if (value instanceof Error) throw value
      return value
    }
    if (url === '/collections/entries') return [collection(1, 'Verbos'), collection(2, 'N5')]
    if (url === '/collections/kanji') return [collection(3, 'Kanji N5')]
    if (options?.method) return saved
    throw new Error(`unexpected ${url}`)
  })
}

// The form's own select menu comes before the directions' ones.
function collectionsMenu(wrapper: VueWrapper) {
  return wrapper.findAllComponents(USelectMenu)[0]!
}

async function mountForm(props: Record<string, unknown> = {}) {
  const wrapper = await mountSuspended(ExerciseForm, { props })
  await flushPromises()
  const form = wrapper.find('form#exercise-form')
  return {
    wrapper,
    async typeName(name: string) {
      await wrapper.find('input[placeholder="p. ej. Verbos: significado"]').setValue(name)
    },
    pickCollections(ids: number[]) {
      collectionsMenu(wrapper)
        .vm.$emit('update:modelValue', ids)
    },
    async submit() {
      await form.trigger('submit')
      await flushPromises()
      await new Promise(resolve => setTimeout(resolve, 0))
      await flushPromises()
    },
    posted: () => api.mock.calls.filter(([, options]) => options?.method),
  }
}

beforeEach(() => {
  api.mockReset()
  respond()
})

describe('ExerciseForm', () => {
  it('creates a word exercise with the default settings and emits it', async () => {
    const form = await mountForm()

    await form.typeName('  Verbos ')
    form.pickCollections([1, 2])
    await form.submit()

    expect(form.posted()).toEqual([['/exercises', {
      method: 'POST',
      body: {
        name: 'Verbos',
        description: null,
        collection_ids: [1, 2],
        settings: saved.settings,
        item_kind: 'entries',
      },
    }]])
    expect(form.wrapper.emitted('saved')).toEqual([[saved]])
  })

  it('requires a collection', async () => {
    const form = await mountForm()

    await form.typeName('Verbos')
    await form.submit()

    expect(form.posted()).toEqual([])
    expect(form.wrapper.text()).toContain('Elige al menos una colección.')
  })

  it('rejects repeated directions, in any order of the shown fields', async () => {
    const form = await mountForm()
    await form.typeName('Verbos')
    form.pickCollections([1])

    form.wrapper.findComponent(DirectionsEditor).vm.$emit('update:modelValue', [
      { prompt: ['writing', 'reading'], answer: 'meaning' },
      { prompt: ['reading', 'writing'], answer: 'meaning' },
    ])
    await form.submit()

    expect(form.posted()).toEqual([])
    expect(form.wrapper.text()).toContain('Hay direcciones repetidas.')
  })

  it('starts collections and fields over when switching to kanji', async () => {
    const form = await mountForm()
    form.pickCollections([1])

    form.wrapper.findComponent(URadioGroup).vm.$emit('update:modelValue', 'kanji')
    await flushPromises()

    expect(api).toHaveBeenCalledWith('/collections/kanji')
    const editor = form.wrapper.findComponent(DirectionsEditor)
    expect(editor.props('kind')).toBe('kanji')
    expect(editor.props('modelValue')).toEqual([{ prompt: ['literal'], answer: 'meaning' }])
    const collections = collectionsMenu(form.wrapper)
    expect(collections.props('modelValue')).toEqual([])
  })

  it('writes the kanji by hand in a kanji exercise, with no options', async () => {
    const form = await mountForm()

    form.wrapper.findComponent(URadioGroup).vm.$emit('update:modelValue', 'kanji')
    await flushPromises()
    form.wrapper.findAllComponents(URadioGroup)[1]!.vm.$emit('update:modelValue', 'card.handwriting')
    await flushPromises()

    expect(form.wrapper.find('input[inputmode="numeric"]').exists()).toBe(false) // no option count
    expect(form.wrapper.findComponent(DirectionsEditor).props('answerFields')).toEqual(['literal'])
    await form.typeName('Escribir N5')
    form.pickCollections([3])
    await form.submit()

    expect(form.posted()).toHaveLength(1)
    const [url, options] = form.posted()[0]!
    expect(url).toBe('/exercises')
    expect(options.body).toMatchObject({
      item_kind: 'kanji',
      settings: {
        type: 'card.handwriting',
        directions: [{ prompt: ['meaning'], answer: 'literal' }],
        back_fields: ['onyomi', 'kunyomi'],
      },
    })
    expect(options.body.settings).not.toHaveProperty('option_count')
  })

  it("writes a word's spelling or reading by hand in a word exercise", async () => {
    const form = await mountForm()
    expect(form.wrapper.find('[data-testid="exercise-type"]').exists()).toBe(true)

    form.wrapper.findAllComponents(URadioGroup)[1]!.vm.$emit('update:modelValue', 'card.handwriting')
    await flushPromises()

    expect(form.wrapper.findComponent(DirectionsEditor).props('answerFields')).toEqual(['writing', 'reading'])
    await form.typeName('Escribir verbos')
    form.pickCollections([1])
    await form.submit()

    const [, options] = form.posted()[0]!
    expect(options.body).toMatchObject({
      item_kind: 'entries',
      settings: {
        type: 'card.handwriting',
        directions: [{ prompt: ['meaning'], answer: 'writing' }],
        back_fields: ['reading'],
      },
    })
  })

  it('edits an exercise without changing its kind', async () => {
    const form = await mountForm({ exercise: saved })

    expect(form.wrapper.findComponent(URadioGroup).props('disabled')).toBe(true)
    await form.typeName('Verbos II')
    await form.submit()

    expect(form.posted()).toEqual([['/exercises/7', {
      method: 'PUT',
      body: { name: 'Verbos II', description: null, collection_ids: [1], settings: saved.settings },
    }]])
  })

  it('shows a deleted collection on the collections field', async () => {
    const notFound = Object.assign(new FetchError('404 Not Found'), { statusCode: 404 })
    respond({ '/exercises': notFound })
    const form = await mountForm()

    await form.typeName('Verbos')
    form.pickCollections([1])
    await form.submit()

    expect(form.wrapper.emitted('saved')).toBeUndefined()
    expect(form.wrapper.text()).toContain('Alguna colección ya no existe')
  })
})
