<template>
  <div class="markdown-body" v-html="rendered"></div>
</template>

<script setup>
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps({
  content: { type: String, default: '' },
})

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${hljs.highlight(str, { language: lang }).value}</code></pre>`
      } catch {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

const rendered = computed(() => md.render(props.content))
</script>

<style>
.markdown-body {
  font-size: 15px;
  line-height: 1.7;
  color: #24292e;
}
.markdown-body h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; margin: 0.67em 0; }
.markdown-body h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: 0.3em; margin: 0.83em 0; }
.markdown-body h3 { font-size: 1.25em; margin: 1em 0; }
.markdown-body h4 { font-size: 1em; margin: 1.33em 0; }
.markdown-body p { margin: 0.5em 0; }
.markdown-body ul, .markdown-body ol { padding-left: 2em; margin: 0.5em 0; }
.markdown-body li { margin: 0.25em 0; }
.markdown-body blockquote {
  border-left: 4px solid #dfe2e5;
  padding: 0 1em;
  color: #6a737d;
  margin: 0.5em 0;
}
.markdown-body code {
  background: #f6f8fa;
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-size: 85%;
}
.markdown-body pre {
  background: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 0.5em 0;
}
.markdown-body pre code {
  background: none;
  padding: 0;
  font-size: 14px;
}
.markdown-body table {
  border-collapse: collapse;
  margin: 0.5em 0;
}
.markdown-body th, .markdown-body td {
  border: 1px solid #dfe2e5;
  padding: 6px 13px;
}
.markdown-body th {
  background: #f6f8fa;
  font-weight: 600;
}
.markdown-body hr {
  border: none;
  border-top: 1px solid #e1e4e8;
  margin: 1.5em 0;
}
.markdown-body a {
  color: #0366d6;
  text-decoration: none;
}
.markdown-body a:hover {
  text-decoration: underline;
}
.markdown-body img {
  max-width: 100%;
}
</style>
