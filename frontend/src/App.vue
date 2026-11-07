<script setup lang="ts">
import { RouterLink, RouterView } from "vue-router";
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="seal">政</span>
        <div>
          <strong>政策智答实验室</strong>
          <small>RAG Knowledge Console</small>
        </div>
      </div>
      <nav>
        <RouterLink to="/">政策问答</RouterLink>
        <RouterLink to="/documents">知识库</RouterLink>
        <RouterLink to="/evaluation">RAG 评估</RouterLink>
        <RouterLink to="/settings">模型设置</RouterLink>
      </nav>
      <div class="notice">
        <b>证据约束</b>
        <span>回答仅依据已导入的政策资料，并提供可追溯的原文引用。</span>
      </div>
    </aside>
    <main>
      <RouterView />
    </main>
  </div>
</template>
