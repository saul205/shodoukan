export function useLastSearch() {
  return useState('lastSearch', () => ({ q: '', lang: 'en' }))
}
