<template>
  <div ref="editorContainer" class="code-editor"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as monaco from 'monaco-editor'

const props = defineProps({
  value: { type: String, default: '' },
  language: { type: String, default: 'markdown' },
  readOnly: { type: Boolean, default: false },
  variableMap: { type: Object, default: () => ({}) },
  targetLine: { type: Number, default: null },
})

const emit = defineEmits(['update:value', 'highlight-done'])

const editorContainer = ref(null)
let editor = null

onMounted(() => {
  editor = monaco.editor.create(editorContainer.value, {
    value: props.value,
    language: props.language,
    theme: 'vs',
    readOnly: props.readOnly,
    minimap: { enabled: false },
    fontSize: 14,
    lineHeight: 22,
    wordWrap: 'on',
    scrollBeyondLastLine: false,
    automaticLayout: true,
    padding: { top: 12, bottom: 12 },
    renderLineHighlight: 'line',
    tabSize: 2,
  })

  editor.onDidChangeModelContent(() => {
    emit('update:value', editor.getValue())
    updateVariableDecorations()
  })
  updateVariableDecorations()
})

let variableDecorations = []

function updateVariableDecorations() {
  if (!editor) return
  const model = editor.getModel()
  if (!model) return

  const text = model.getValue()
  const decorations = []
  const regex = /!\{([A-Za-z_][A-Za-z0-9_]*)\}/g
  let match

  while ((match = regex.exec(text)) !== null) {
    const startPos = model.getPositionAt(match.index)
    const endPos = model.getPositionAt(match.index + match[0].length)
    const varName = match[1]
    const varInfo = props.variableMap[varName]
    const hoverText = varInfo
      ? `**Variable:** \`${varName}\`\n\n**Value:** \`${varInfo.type === 'secret' ? '******' : varInfo.value}\`\n\n**Scope:** ${varInfo.scope}`
      : `**Variable:** \`${varName}\` (unresolved)`
    decorations.push({
      range: new monaco.Range(startPos.lineNumber, startPos.column, endPos.lineNumber, endPos.column),
      options: {
        inlineClassName: 'variable-placeholder',
        hoverMessage: { value: hoverText },
      },
    })
  }

  variableDecorations = editor.deltaDecorations(variableDecorations, decorations)
}

watch(() => props.variableMap, () => {
  updateVariableDecorations()
}, { deep: true })

watch(() => props.value, (newVal) => {
  if (editor && editor.getValue() !== newVal) {
    editor.setValue(newVal)
  }
})

watch(() => props.language, (newLang) => {
  if (editor) {
    const model = editor.getModel()
    if (model) {
      monaco.editor.setModelLanguage(model, newLang)
    }
  }
})

// Target line: scroll to line and highlight
let lineHighlightDecorations = []
let lineHighlightTimeout = null

watch(() => props.targetLine, (lineNum) => {
  if (!lineNum || !editor) return
  if (lineHighlightTimeout) clearTimeout(lineHighlightTimeout)

  editor.revealLineInCenter(lineNum)
  lineHighlightDecorations = editor.deltaDecorations(lineHighlightDecorations, [{
    range: new monaco.Range(lineNum, 1, lineNum, 1),
    options: {
      isWholeLine: true,
      className: 'highlight-target-line',
    },
  }])

  lineHighlightTimeout = setTimeout(() => {
    lineHighlightDecorations = editor.deltaDecorations(lineHighlightDecorations, [])
    lineHighlightTimeout = null
  }, 4000)

  emit('highlight-done')
}, { flush: 'post' })

onBeforeUnmount(() => {
  if (editor) {
    editor.dispose()
    editor = null
  }
})
</script>

<style scoped>
.code-editor {
  width: 100%;
  height: 100%;
  min-height: 400px;
}
:deep(.variable-placeholder) {
  background-color: rgba(233, 69, 96, 0.15);
  outline: 1px solid rgba(233, 69, 96, 0.3);
  border-radius: 3px;
}
:deep(.highlight-target-line) {
  background: rgba(255, 213, 79, 0.4);
}
</style>
