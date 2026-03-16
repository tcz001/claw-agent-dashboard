<template>
  <div class="file-tree">
    <div v-for="node in files" :key="node.path">
      <div v-if="node.type === 'file'"
        class="tree-file"
        :class="{ active: currentPath === node.path }"
        @click="$emit('select', node.path)"
      >
        <el-icon><Document /></el-icon>
        <span>{{ node.name }}</span>
      </div>
      <div v-else class="tree-dir">
        <div class="tree-dir-name" @click="toggleDir(node.path)">
          <el-icon>
            <ArrowRight v-if="!expanded[node.path]" />
            <ArrowDown v-else />
          </el-icon>
          <el-icon><Folder /></el-icon>
          <span>{{ node.name }}</span>
        </div>
        <div v-if="expanded[node.path]" class="tree-children">
          <FileTree
            :files="node.children || []"
            :current-path="currentPath"
            @select="$emit('select', $event)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { Document, Folder, ArrowRight, ArrowDown } from '@element-plus/icons-vue'

defineProps({
  files: { type: Array, default: () => [] },
  currentPath: { type: String, default: '' },
})

defineEmits(['select'])

const expanded = reactive({})

function toggleDir(path) {
  expanded[path] = !expanded[path]
}
</script>

<style scoped>
.tree-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px 4px 16px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
}
.tree-file:hover {
  background: #f0f2f5;
}
.tree-file.active {
  background: #e6f0ff;
  color: #409eff;
}
.tree-dir-name {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  cursor: pointer;
  font-size: 13px;
}
.tree-dir-name:hover {
  background: #f0f2f5;
}
.tree-children {
  padding-left: 16px;
}
</style>
