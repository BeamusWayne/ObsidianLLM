import { ref, onUnmounted } from 'vue'

/**
 * Horizontal drag-to-resize.
 * @param {number} initial  - initial size in px
 * @param {object} opts
 *   min      {number}  - minimum px
 *   max      {number}  - maximum px
 *   inverted {boolean} - true when dragging left makes the panel larger (right-side panels)
 */
export function useResizer(initial, { min = 100, max = 800, inverted = false } = {}) {
  const size = ref(initial)
  const dragging = ref(false)
  let startX = 0
  let startSize = 0

  function start(e) {
    dragging.value = true
    startX = e.clientX
    startSize = size.value
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', stop)
    document.body.style.userSelect = 'none'
    document.body.style.cursor = 'col-resize'
    e.preventDefault()
  }

  function move(e) {
    if (!dragging.value) return
    const delta = inverted ? startX - e.clientX : e.clientX - startX
    size.value = Math.min(max, Math.max(min, startSize + delta))
  }

  function stop() {
    dragging.value = false
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', stop)
    document.body.style.userSelect = ''
    document.body.style.cursor = ''
  }

  onUnmounted(stop)

  return { size, dragging, start }
}
