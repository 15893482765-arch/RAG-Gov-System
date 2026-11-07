<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { api } from "../api";

const form = reactive({ provider: "ollama", model: "", base_url: "" });
const saved = ref(false);
const configured = ref(false);

async function load() {
  const { data } = await api.get("/config/model");
  form.provider = data.provider;
  form.model = data.model;
  form.base_url = data.base_url;
  configured.value = data.configured;
}
async function save() {
  const { data } = await api.put("/config/model", {
    provider: form.provider,
    model: form.model,
    base_url: form.base_url,
  });
  configured.value = data.configured;
  saved.value = true;
  setTimeout(() => (saved.value = false), 1800);
}
function useProviderDefaults() {
  if (form.provider === "deepseek") {
    form.model = "deepseek-v4-flash";
    form.base_url = "https://api.deepseek.com";
  } else {
    form.model = "qwen2.5:7b";
    form.base_url = "http://127.0.0.1:11434";
  }
}
onMounted(load);
</script>


<template>
  <section class="page narrow">
    <header class="page-header">
      <div>
        <p class="eyebrow">MODEL ROUTING</p>
        <h1>模型设置</h1>
        <p>业务链路不绑定厂商，可在 Ollama 与 DeepSeek 之间切换。</p>
      </div>
    </header>
    <div class="card form-card">
      <label>服务提供方
        <select v-model="form.provider" @change="useProviderDefaults">
          <option value="ollama">Ollama（本地）</option>
          <option value="deepseek">DeepSeek（在线）</option>
        </select>
      </label>
      <label>模型名称
        <select v-if="form.provider === 'deepseek'" v-model="form.model">
          <option value="deepseek-v4-flash">deepseek-v4-flash（快速响应）</option>
          <option value="deepseek-v4-pro">deepseek-v4-pro（更高质量）</option>
          <option value="deepseek-chat">deepseek-chat（2026-07-24 弃用）</option>
          <option value="deepseek-reasoner">deepseek-reasoner（2026-07-24 弃用）</option>
        </select>
        <input v-else v-model="form.model" />
      </label>
      <label>服务地址<input v-model="form.base_url" /></label>
      <div class="setting-note">
        <b>{{ configured ? "配置可用" : "尚未完整配置" }}</b>
        <span v-if="form.provider === 'deepseek'">
          API Key 仅从后端环境变量读取。建议使用 v4-flash 或 v4-pro。
        </span>
        <span v-else>请确保本机 Ollama 服务已经启动并下载对应模型。</span>
      </div>
      <button @click="save">{{ saved ? "已保存" : "保存并切换" }}</button>
    </div>
  </section>
</template>
