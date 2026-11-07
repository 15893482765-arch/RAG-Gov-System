import { createRouter, createWebHistory } from "vue-router";
import ChatView from "./views/ChatView.vue";
import DocumentsView from "./views/DocumentsView.vue";
import EvaluationView from "./views/EvaluationView.vue";
import SettingsView from "./views/SettingsView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: ChatView },
    { path: "/documents", component: DocumentsView },
    { path: "/evaluation", component: EvaluationView },
    { path: "/settings", component: SettingsView },
  ],
});

