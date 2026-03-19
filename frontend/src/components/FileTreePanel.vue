<template>
  <div class="file-tree-panel">
    <!-- Search input -->
    <div class="search-box">
      <el-input
        v-model="store.fileSearchQuery"
        :placeholder="t('search.placeholder')"
        :prefix-icon="Search"
        clearable
        size="small"
        @keyup.enter="handleSearch"
        @clear="store.clearFileSearch()"
      />
    </div>

    <!-- Search results view -->
    <el-scrollbar v-if="store.fileSearchResults">
      <div v-if="store.fileSearchLoading" class="search-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        {{ t('search.searching') }}
      </div>
      <div v-else-if="store.fileSearchResults.total_matches === 0" class="search-empty">
        {{ t('search.noResults') }}
      </div>
      <div v-else class="search-results">
        <div class="search-summary">
          {{ t('search.matchCount', { count: store.fileSearchResults.total_matches, files: store.fileSearchResults.results.length }) }}
        </div>
        <div v-for="fileResult in store.fileSearchResults.results" :key="fileResult.file_path" class="search-file-group">
          <div class="search-file-header" @click="toggleSearchFile(fileResult.file_path)">
            <el-icon style="font-size: 10px">
              <ArrowRight v-if="collapsedSearchFiles.has(fileResult.file_path)" />
              <ArrowDown v-else />
            </el-icon>
            <span class="search-file-name">{{ fileResult.file_path }}</span>
            <span class="search-match-count">{{ fileResult.matches.length }}</span>
          </div>
          <div v-if="!collapsedSearchFiles.has(fileResult.file_path)" class="search-matches">
            <div
              v-for="match in fileResult.matches"
              :key="match.line_number"
              class="search-match-item"
              @click="openSearchResult(fileResult.file_path, match.line_number)"
            >
              <span class="search-line-num">{{ match.line_number }}</span>
              <span class="search-line-content" v-html="highlightMatch(match.line_content, store.fileSearchQuery)"></span>
            </div>
          </div>
        </div>
      </div>
    </el-scrollbar>

    <!-- Normal file tree view -->
    <el-scrollbar v-else>
      <!-- Blueprint derivation badge -->
      <span v-if="store.derivationStatus?.is_derived" class="derived-badge">
        🔗 {{ t('management.derivedFrom', { name: store.derivationStatus.blueprint_name }) }}
      </span>

      <!-- Core files -->
      <div class="section-label">{{ t('sidebar.coreFiles') }}</div>
      <div
        v-for="file in store.agentFiles"
        :key="file.path"
        class="file-item"
        :class="{ active: store.currentFile?.path === file.path && !store.currentFile?._globalSource }"
      >
        <el-checkbox
          class="file-checkbox"
          :model-value="store.isFileSelected(store.currentAgent.name, file.path)"
          @change="store.toggleFileSelection(store.currentAgent.name, file.path)"
          @click.stop
          size="small"
        />
        <div class="file-item-content" @click="store.selectFile(file.path)">
          <el-icon><Document /></el-icon>
          <span>{{ file.name }}</span>
          <span v-if="store.isFileSynced(file.path) === true" class="sync-icon synced" title="Synced">🔗</span>
          <span v-else-if="store.isFileSynced(file.path) === false" class="sync-icon overridden" title="Overridden">✏️</span>
          <el-tag v-if="file.has_translation" size="small" type="success" class="trans-tag">{{ t('sidebar.translated') }}</el-tag>
        </div>
      </div>

      <!-- Other files -->
      <div v-if="store.agentOtherFiles.length > 0">
        <div class="section-label clickable" @click="otherFilesExpanded = !otherFilesExpanded">
          <el-icon style="font-size: 10px; margin-right: 2px">
            <ArrowRight v-if="!otherFilesExpanded" />
            <ArrowDown v-else />
          </el-icon>
          {{ t('sidebar.otherFiles') }}
        </div>
        <div v-if="otherFilesExpanded" class="other-files-section">
          <FileTree
            :files="store.agentOtherFiles"
            :current-path="store.currentFile?.path"
            @select="store.selectFile($event)"
          />
        </div>
      </div>

      <!-- Skills -->
      <div v-if="store.agentSkills.length > 0" class="section-label">{{ t('sidebar.skills') }}</div>
      <div v-for="skill in store.agentSkills" :key="skill.name" class="skill-group">
        <div class="skill-header" @click="toggleSkill(skill.name)">
          <el-icon>
            <ArrowRight v-if="!expandedSkills[skill.name]" />
            <ArrowDown v-else />
          </el-icon>
          <el-icon><Files /></el-icon>
          <span class="skill-name">{{ skill.display_name }}</span>
        </div>
        <div v-if="expandedSkills[skill.name]" class="skill-files">
          <FileTree
            :files="store.skillFilesMap[skill.name] || []"
            :current-path="store.currentFile?.path"
            @select="store.selectFile($event)"
          />
        </div>
      </div>

      <!-- Memory -->
      <div v-if="store.agentMemory.length > 0">
        <div class="section-label clickable" @click="memoryExpanded = !memoryExpanded">
          <el-icon style="font-size: 10px; margin-right: 2px">
            <ArrowRight v-if="!memoryExpanded" />
            <ArrowDown v-else />
          </el-icon>
          {{ t('sidebar.memory') }}
        </div>
        <div v-if="memoryExpanded">
          <div
            v-for="file in store.agentMemory"
            :key="file.path"
            class="file-item"
            :class="{ active: store.currentFile?.path === file.path && !store.currentFile?._globalSource }"
          >
            <el-checkbox
              class="file-checkbox"
              :model-value="store.isFileSelected(store.currentAgent.name, file.path)"
              @change="store.toggleFileSelection(store.currentAgent.name, file.path)"
              @click.stop
              size="small"
            />
            <div class="file-item-content" @click="store.selectFile(file.path)">
              <el-icon><Document /></el-icon>
              <span>{{ file.name }}</span>
              <el-tag v-if="file.has_translation" size="small" type="success" class="trans-tag">{{ t('sidebar.translated') }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- Global Skills -->
      <div v-if="store.globalSkillSources.length > 0" class="global-skills-section">
        <div class="section-label clickable" @click="globalSkillsExpanded = !globalSkillsExpanded">
          <el-icon style="font-size: 10px; margin-right: 2px">
            <ArrowRight v-if="!globalSkillsExpanded" />
            <ArrowDown v-else />
          </el-icon>
          🌐 {{ t('sidebar.globalSkills') }}
        </div>

        <div v-if="globalSkillsExpanded" class="global-skills-content">
          <div v-for="src in store.globalSkillSources" :key="src.source" class="source-group">
            <div class="source-header" @click="toggleSource(src.source)">
              <el-icon>
                <ArrowRight v-if="!expandedSources[src.source]" />
                <ArrowDown v-else />
              </el-icon>
              <el-icon><Folder /></el-icon>
              <span>{{ src.name }}</span>
            </div>

            <div v-if="expandedSources[src.source]" class="source-skills">
              <div
                v-for="skill in (store.globalSkills[src.source] || [])"
                :key="skill.name"
                class="skill-group"
              >
                <div class="skill-header" @click="toggleGlobalSkill(src.source, skill.name)">
                  <el-icon>
                    <ArrowRight v-if="!expandedGlobalSkills[src.source + '/' + skill.name]" />
                    <ArrowDown v-else />
                  </el-icon>
                  <el-icon><Files /></el-icon>
                  <span class="skill-name">{{ skill.display_name }}</span>
                </div>

                <div v-if="expandedGlobalSkills[src.source + '/' + skill.name]" class="skill-files">
                  <FileTree
                    :files="store.globalSkillFilesMap[src.source + '/' + skill.name] || []"
                    :current-path="store.currentFile?.path"
                    @select="store.selectGlobalFile(src.source, $event)"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Folder, Document, Files,
  ArrowRight, ArrowDown,
  Search, Loading,
} from '@element-plus/icons-vue'
import { useAgentStore } from '../stores/agent'
import FileTree from './FileTree.vue'

const { t } = useI18n()
const store = useAgentStore()
const expandedSkills = reactive({})
const expandedSources = reactive({})
const expandedGlobalSkills = reactive({})
const globalSkillsExpanded = ref(false)
const memoryExpanded = ref(false)
const otherFilesExpanded = ref(false)

const collapsedSearchFiles = ref(new Set())

function handleSearch() {
  if (store.fileSearchQuery.trim()) {
    collapsedSearchFiles.value = new Set()
    store.searchAgentFiles(store.fileSearchQuery)
  }
}

function toggleSearchFile(filePath) {
  const next = new Set(collapsedSearchFiles.value)
  if (next.has(filePath)) {
    next.delete(filePath)
  } else {
    next.add(filePath)
  }
  collapsedSearchFiles.value = next
}

function openSearchResult(filePath, lineNumber) {
  store.selectFile(filePath, lineNumber)
}

function highlightMatch(text, query) {
  if (!query) return text
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const regex = new RegExp(`(${escaped})`, 'gi')
  return text.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(regex, '<mark>$1</mark>')
}

async function toggleSkill(skillName) {
  expandedSkills[skillName] = !expandedSkills[skillName]
  if (expandedSkills[skillName]) {
    await store.loadSkillFiles(skillName)
  }
}

async function toggleSource(source) {
  expandedSources[source] = !expandedSources[source]
  if (expandedSources[source]) {
    await store.loadGlobalSkills(source)
  }
}

async function toggleGlobalSkill(source, skillName) {
  const key = `${source}/${skillName}`
  expandedGlobalSkills[key] = !expandedGlobalSkills[key]
  if (expandedGlobalSkills[key]) {
    await store.loadGlobalSkillFiles(source, skillName)
  }
}
</script>

<style scoped>
.file-tree-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}
.section-label {
  padding: 6px 16px 2px 16px;
  font-size: 11px;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.section-label.clickable {
  cursor: pointer;
  display: flex;
  align-items: center;
}
.section-label.clickable:hover {
  color: #606266;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 16px 4px 20px;
  font-size: 13px;
  transition: background 0.15s;
}
.file-item:hover {
  background: #ebeef5;
}
.file-item.active {
  background: #e6f0ff;
  color: #409eff;
}
.file-checkbox {
  flex-shrink: 0;
}
.file-item-content {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
  padding: 2px 0;
}
.file-item-content span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trans-tag {
  margin-left: auto;
  font-size: 10px !important;
  height: 18px !important;
  line-height: 16px !important;
  padding: 0 4px !important;
  flex-shrink: 0;
}
.skill-group {
  margin-left: 0;
}
.skill-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px 6px 16px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
}
.skill-header:hover {
  background: #ebeef5;
}
.skill-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.skill-files {
  padding-left: 20px;
}
.other-files-section {
  padding-left: 20px;
}
.derived-badge {
  display: block;
  font-size: 11px;
  color: var(--el-color-primary);
  padding: 4px 8px;
  margin-bottom: 4px;
}
.sync-icon {
  margin-left: 4px;
  font-size: 11px;
}
.sync-icon.synced {
  opacity: 0.5;
}
.sync-icon.overridden {
  color: var(--el-color-warning);
}
/* Global skills */
.global-skills-section {
  border-top: 1px solid #ebeef5;
  margin-top: 8px;
}
.global-skills-content {
  padding-bottom: 4px;
}
.source-group {
  margin-left: 0;
}
.source-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px 6px 28px;
  cursor: pointer;
  font-size: 13px;
  color: #606266;
  transition: background 0.15s;
}
.source-header:hover {
  background: #ebeef5;
}
.source-skills {
  padding-left: 12px;
}
.search-box {
  padding: 8px 12px 4px;
  flex-shrink: 0;
}
.search-loading, .search-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: #909399;
  font-size: 13px;
}
.search-summary {
  padding: 4px 16px;
  font-size: 11px;
  color: #909399;
}
.search-file-group {
  margin-bottom: 2px;
}
.search-file-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  background: #f0f2f5;
}
.search-file-header:hover {
  background: #ebeef5;
}
.search-file-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: monospace;
}
.search-match-count {
  font-size: 10px;
  color: #909399;
  background: #e4e7ed;
  padding: 0 6px;
  border-radius: 8px;
}
.search-match-item {
  display: flex;
  gap: 8px;
  padding: 3px 16px 3px 28px;
  cursor: pointer;
  font-size: 12px;
  line-height: 1.5;
  transition: background 0.15s;
}
.search-match-item:hover {
  background: #ebeef5;
}
.search-line-num {
  color: #909399;
  font-family: monospace;
  min-width: 28px;
  text-align: right;
  flex-shrink: 0;
}
.search-line-content {
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #303133;
}
.search-line-content :deep(mark) {
  background: #ffd54f;
  color: #333;
  padding: 0 1px;
  border-radius: 2px;
}
</style>
