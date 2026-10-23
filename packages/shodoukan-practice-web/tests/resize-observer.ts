import { vi } from 'vitest'

// A ResizeObserver that reports `room` for every box as soon as it's observed,
// so components that fit a pad to its box draw one in tests.
export function stubResizeObserver(room = { width: 400, height: 400 }) {
  vi.stubGlobal('ResizeObserver', class {
    constructor(private callback: ResizeObserverCallback) {}
    observe() {
      this.callback([{ contentRect: room } as ResizeObserverEntry], this as unknown as ResizeObserver)
    }
    unobserve() {}
    disconnect() {}
  })
}
