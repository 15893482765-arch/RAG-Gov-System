<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { api } from "../api";

const datasets = ref<any[]>([]);
const runs = ref<any[]>([]);
const selectedRun = ref<any>();
const caseResults = ref<any[]>([]);
const expanded = ref<string>();
const datasetForm = reactive({
  name: "",
  question: "",
  reference_answer: "",
  question_type: "direct",
  should_refuse: false,
});
const runForm = reactive({
  dataset_id: "",
  name: "",
  mode: "full",
  top_k: undefined as number | undefined,
  rerank_top_k: undefined as number | undefined,
  min_evidence_score: 0.25,
  enable_judge: false,
});

const metricLabels: Record<string, string> = {
  recall_at_k: "Recall@K",
  mrr: "MRR",
  citation_precision: "引用准确率",
  refusal_accuracy: "拒答准确率",
  factual_accuracy: "事实准确率",
  faithfulness: "忠实度",
  relevance: "相关性",
  hallucination_rate: "幻觉率",
  average_latency_ms: "平均延迟",
};
const displayMetrics = computed(() =>
  Object.entries(selectedRun.value?.metrics || {}).filter(([key]) => key !== "case_count"),
);
const datasetName = computed(() => datasetForm.name.trim());
const datasetNameExists = computed(() =>
  datasets.value.some((item) => item.name.trim() === datasetName.value),
);
const runName = computed(() => runForm.name.trim());
const canStartRun = computed(
  () => Boolean(runForm.dataset_id && runName.value && runForm.top_k && runForm.rerank_top_k),
);

async function load() {
  [datasets.value, runs.value] = await Promise.all([
    api.get("/evaluation/datasets").then((r) => r.data),
    api.get("/evaluation/runs").then((r) => r.data),
  ]);
  if (!runForm.dataset_id && datasets.value[0]) runForm.dataset_id = datasets.value[0].id;
}
async function createDataset() {
  if (!datasetName.value || datasetNameExists.value || !datasetForm.question.trim()) return;
  await api.post("/evaluation/datasets", {
    name: datasetName.value,
    cases: [
      {
        question: datasetForm.question,
        reference_answer: datasetForm.reference_answer,
        question_type: datasetForm.question_type,
        should_refuse: datasetForm.should_refuse,
      },
    ],
  });
  datasetForm.name = "";
  datasetForm.question = "";
  datasetForm.reference_answer = "";
  datasetForm.question_type = "direct";
  datasetForm.should_refuse = false;
  await load();
}
async function importFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  await api.post("/evaluation/datasets/import", form);
  await load();
}
async function startRun() {
  if (!canStartRun.value) return;
  await api.post("/evaluation/runs", {
    ...runForm,
    name: runName.value,
    top_k: Number(runForm.top_k),
    rerank_top_k: Number(runForm.rerank_top_k),
  });
  await load();
}
async function inspect(run: any) {
  selectedRun.value = (await api.get(`/evaluation/runs/${run.id}`)).data;
  caseResults.value = (await api.get(`/evaluation/runs/${run.id}/cases`)).data;
}
async function saveManual(item: any) {
  await api.put(`/evaluation/results/${item.id}/manual-score`, {
    faithfulness: item.manual_score.faithfulness,
    relevance: item.manual_score.relevance,
    factual_accuracy: item.manual_score.factual_accuracy,
    notes: item.manual_score.notes || "",
  });
  item.manualSaved = true;
  setTimeout(() => (item.manualSaved = false), 1500);
}
function formatMetric(key: string, value: any) {
  if (key === "average_latency_ms") return `${value} ms`;
  return `${(Number(value) * 100).toFixed(1)}%`;
}
onMounted(load);
</script>

<template>
  <section class="page">
    <header class="page-header">
      <div>
        <p class="eyebrow">RAG EVALUATION</p>
        <h1>效果评估实验台</h1>
        <p>用固定测试集比较检索方案，定位召回、引用和幻觉问题。</p>
      </div>
      <a
        v-if="selectedRun"
        class="button secondary"
        :href="`/api/evaluation/runs/${selectedRun.id}/report?format=csv`"
      >导出 CSV</a>
    </header>

    <div class="grid three">
      <div class="card evaluation-builder">
        <h2>1. 建立测试集</h2>
        <p class="section-tip">先录入一个测试问题，也可以直接导入 CSV / JSONL 批量创建。</p>
        <label>测试集名称<input v-model="datasetForm.name" placeholder="例如：数字化补贴评估集" /></label>
        <p v-if="datasetNameExists" class="field-error">测试集名称已存在，请换一个名称。</p>
        <label>问题<textarea v-model="datasetForm.question" rows="3" /></label>
        <label>参考答案<textarea v-model="datasetForm.reference_answer" rows="3" /></label>
        <div class="case-options">
          <label>问题类型
            <select v-model="datasetForm.question_type">
              <option value="direct">单段问答</option>
              <option value="multi_hop">多段综合</option>
              <option value="exact_fact">精确事实</option>
              <option value="ambiguous">模糊问题</option>
              <option value="out_of_scope">知识库外</option>
              <option value="adversarial">错误前提</option>
            </select>
          </label>
          <label class="check option-check">
            <input v-model="datasetForm.should_refuse" type="checkbox" />
            <span>
              <b>应拒答</b>
              <small>知识库不足或问题越界时勾选</small>
            </span>
          </label>
        </div>
        <button
          class="create-case"
          :disabled="!datasetName || datasetNameExists || !datasetForm.question.trim()"
          @click="createDataset"
        >
          添加测试用例
        </button>
        <label class="import evaluation-import">
          <span>导入 CSV / JSONL</span>
          <small>支持批量问题、参考答案、标准证据和拒答标记</small>
          <input type="file" @change="importFile" />
        </label>
      </div>

      <div class="card">
        <h2>2. 配置对比实验</h2>
        <label>测试集
          <select v-model="runForm.dataset_id">
            <option v-for="item in datasets" :key="item.id" :value="item.id">
              {{ item.name }}（{{ item.case_count }}题）
            </option>
          </select>
        </label>
        <label>实验名称<input v-model="runForm.name" placeholder="例如：完整 RAG 评估" /></label>
        <label>RAG 方案
          <select v-model="runForm.mode">
            <option value="vector">仅向量检索</option>
            <option value="hybrid">混合检索</option>
            <option value="hybrid_rerank">混合检索 + 重排序</option>
            <option value="full">完整证据约束</option>
          </select>
        </label>
        <div class="inline">
          <label>召回数<input v-model.number="runForm.top_k" type="number" min="1" placeholder="例如：8" /></label>
          <label>最终证据<input v-model.number="runForm.rerank_top_k" type="number" min="1" placeholder="例如：4" /></label>
        </div>
        <label>拒答阈值 {{ runForm.min_evidence_score }}
          <input v-model.number="runForm.min_evidence_score" type="range" min="0" max="1" step="0.05" />
        </label>
        <label class="check"><input v-model="runForm.enable_judge" type="checkbox" />启用 LLM Judge</label>
        <button :disabled="!canStartRun" @click="startRun">启动批量评估</button>
      </div>

      <div class="card">
        <h2>3. 历史运行</h2>
        <div v-if="!runs.length" class="empty">暂无评估记录</div>
        <button
          v-for="run in runs"
          :key="run.id"
          class="run-row"
          @click="inspect(run)"
        >
          <span><b>{{ run.name }}</b><small>{{ run.rag_config.mode }}</small></span>
          <i :class="run.status">{{ run.status }}</i>
        </button>
      </div>
    </div>

    <template v-if="selectedRun">
      <div class="metric-grid">
        <div v-for="[key, value] in displayMetrics" :key="key" class="metric">
          <span>{{ metricLabels[key] || key }}</span>
          <b>{{ formatMetric(key, value) }}</b>
        </div>
      </div>
      <div class="card results">
        <div class="card-title">
          <h2>逐题诊断</h2>
          <span>{{ selectedRun.status }}</span>
        </div>
        <div v-for="item in caseResults" :key="item.id" class="case">
          <button class="case-head" @click="expanded = expanded === item.id ? undefined : item.id">
            <span>
              <b>{{ item.question }}</b>
              <small>{{ item.refused ? "系统拒答" : "已回答" }} · {{ item.latency_ms }} ms</small>
            </span>
            <span class="case-score">
              Recall {{ formatMetric("recall_at_k", item.metrics.recall_at_k) }}
            </span>
          </button>
          <div v-if="expanded === item.id" class="trace">
            <h3>系统回答</h3><p>{{ item.answer }}</p>
            <h3>参考答案</h3><p>{{ item.reference_answer || "未设置" }}</p>
            <h3>检索路径</h3>
            <dl>
              <dt>查询改写</dt><dd>{{ item.trace.rewritten_query }}</dd>
              <dt>向量召回</dt><dd>{{ item.trace.vector_results?.length || 0 }} 条</dd>
              <dt>BM25 召回</dt><dd>{{ item.trace.keyword_results?.length || 0 }} 条</dd>
              <dt>最终证据</dt><dd>{{ item.trace.final_evidence?.length || 0 }} 条</dd>
            </dl>
            <div class="manual-review">
              <h3>教师人工复核（0-1）</h3>
              <div class="inline">
                <label>忠实度<input v-model.number="item.manual_score.faithfulness" type="number" min="0" max="1" step="0.1" /></label>
                <label>相关性<input v-model.number="item.manual_score.relevance" type="number" min="0" max="1" step="0.1" /></label>
                <label>事实准确率<input v-model.number="item.manual_score.factual_accuracy" type="number" min="0" max="1" step="0.1" /></label>
              </div>
              <label>复核备注<textarea v-model="item.manual_score.notes" rows="2" /></label>
              <button class="secondary" @click="saveManual(item)">
                {{ item.manualSaved ? "已保存" : "保存人工评分" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-if="runs.length" class="card comparison">
      <div class="card-title"><h2>方案横向对比</h2><span>配置快照</span></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>实验</th><th>方案</th><th>Recall@K</th><th>MRR</th>
              <th>引用准确率</th><th>拒答准确率</th><th>幻觉率</th><th>延迟</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs.filter((item) => item.status === 'completed')" :key="run.id">
              <td>{{ run.name }}</td>
              <td>{{ run.rag_config.mode }}</td>
              <td>{{ formatMetric("recall_at_k", run.metrics.recall_at_k) }}</td>
              <td>{{ formatMetric("mrr", run.metrics.mrr) }}</td>
              <td>{{ formatMetric("citation_precision", run.metrics.citation_precision) }}</td>
              <td>{{ formatMetric("refusal_accuracy", run.metrics.refusal_accuracy) }}</td>
              <td>{{ formatMetric("hallucination_rate", run.metrics.hallucination_rate) }}</td>
              <td>{{ formatMetric("average_latency_ms", run.metrics.average_latency_ms) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
