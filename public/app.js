const statsElement = document.querySelector("#stats");
const messageElement = document.querySelector("#message");
const openCreateButton = document.querySelector("#open-create-button");
const logoutButton = document.querySelector("#logout-button");
const currentUserElement = document.querySelector("#current-user");
const detailSection = document.querySelector("#detail-section");
const detailEyebrow = document.querySelector("#detail-eyebrow");
const detailTitle = document.querySelector("#detail-title");
const detailContent = document.querySelector("#detail-content");

const dashboardSection = document.querySelector("#dashboard-section");
const recentContentList = document.querySelector("#recent-content-list");
const syncStatusList = document.querySelector("#sync-status-list");
const platformList = document.querySelector("#platform-list");

const influencerSection = document.querySelector("#influencer-section");
const influencerListElement = document.querySelector("#influencer-list");
const influencerResultCountElement = document.querySelector("#influencer-result-count");
const influencerDialog = document.querySelector("#influencer-dialog");
const influencerForm = document.querySelector("#influencer-form");
const influencerFormTitle = document.querySelector("#influencer-form-title");
const influencerFormEyebrow = document.querySelector("#influencer-form-eyebrow");
const influencerKeywordInput = document.querySelector("#influencer-keyword-input");
const influencerCategoryToggle = document.querySelector("#influencer-category-toggle");
const influencerCategorySummary = document.querySelector("#influencer-category-summary");
const influencerCategoryOptionsElement = document.querySelector("#influencer-category-options");
const platformFilter = document.querySelector("#platform-filter");
const influencerCategoryFilter = document.querySelector("#influencer-category-filter");
const influencerOwnerFilter = document.querySelector("#influencer-owner-filter");
const followersMinFilter = document.querySelector("#followers-min-filter");
const followersMaxFilter = document.querySelector("#followers-max-filter");

const projectSection = document.querySelector("#project-section");
const projectListElement = document.querySelector("#project-list");
const projectResultCountElement = document.querySelector("#project-result-count");
const projectDialog = document.querySelector("#project-dialog");
const projectForm = document.querySelector("#project-form");
const projectFormTitle = document.querySelector("#project-form-title");
const projectFormEyebrow = document.querySelector("#project-form-eyebrow");
const projectKeywordInput = document.querySelector("#project-keyword-input");
const projectStatusFilter = document.querySelector("#project-status-filter");
const projectOwnerFilter = document.querySelector("#project-owner-filter");

const contentSection = document.querySelector("#content-section");
const contentListElement = document.querySelector("#content-list");
const contentResultCountElement = document.querySelector("#content-result-count");
const contentDialog = document.querySelector("#content-dialog");
const contentForm = document.querySelector("#content-form");
const contentFormTitle = document.querySelector("#content-form-title");
const contentFormEyebrow = document.querySelector("#content-form-eyebrow");
const contentKeywordInput = document.querySelector("#content-keyword-input");
const contentPlatformFilter = document.querySelector("#content-platform-filter");
const contentProjectFilter = document.querySelector("#content-project-filter");
const viewsMinFilter = document.querySelector("#views-min-filter");
const viewsMaxFilter = document.querySelector("#views-max-filter");
const interactionsMinFilter = document.querySelector("#interactions-min-filter");
const interactionsMaxFilter = document.querySelector("#interactions-max-filter");
const contentInfluencerSelect = document.querySelector("#content-influencer-select");
const contentProjectSelect = document.querySelector("#content-project-select");

let influencers = [];
let projects = [];
let contents = [];
let dashboardSummary = null;
let activeView = "dashboard";
let activeDetail = null;
const validViews = new Set(["dashboard", "influencers", "projects", "contents"]);
const influencerCategoryOptions = [
  "影视娱乐",
  "音乐",
  "生活",
  "人文艺术",
  "摄影",
  "旅游",
  "搞笑趣闻",
  "情感",
  "教育",
  "母婴育儿",
  "财经",
  "游戏动漫",
  "健康",
  "运动",
  "科学科普",
  "科技",
  "互联网",
  "职场管理",
  "美食",
  "时尚",
  "美妆",
  "萌宠",
  "汽车",
];
const profileUrlDomainMap = {
  小红书: ["xiaohongshu.com", "xhslink.com"],
  抖音: ["douyin.com", "v.douyin.com", "iesdouyin.com"],
  B站: ["bilibili.com", "space.bilibili.com", "b23.tv"],
  视频号: ["channels.weixin.qq.com", "weixin.qq.com"],
  微博: ["weibo.com", "weibo.cn"],
  快手: ["kuaishou.com", "v.kuaishou.com", "live.kuaishou.com"],
};

function splitCategoryTags(value) {
  return String(value || "")
    .split(/[、,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function renderInfluencerCategoryOptions() {
  if (!influencerCategoryOptionsElement) {
    return;
  }
  influencerCategoryOptionsElement.innerHTML = influencerCategoryOptions
    .map(
      (tag) => `
        <label class="tag-option">
          <input type="checkbox" name="category_tags" value="${escapeHtml(tag)}" />
          <span>${escapeHtml(tag)}</span>
        </label>
      `,
    )
    .join("");
  updateInfluencerCategorySummary();
}

function renderInfluencerCategoryFilterOptions() {
  if (!influencerCategoryFilter) {
    return;
  }
  influencerCategoryFilter.innerHTML = `
    <option value="">全部分类</option>
    ${influencerCategoryOptions
      .map((tag) => `<option value="${escapeHtml(tag)}">${escapeHtml(tag)}</option>`)
      .join("")}
  `;
}

function setInfluencerCategoryTags(value) {
  const selectedTags = new Set(splitCategoryTags(value));
  influencerForm.querySelectorAll('input[name="category_tags"]').forEach((input) => {
    input.checked = selectedTags.has(input.value);
  });
  updateInfluencerCategorySummary();
}

function getSelectedInfluencerCategoryTags() {
  return Array.from(influencerForm.querySelectorAll('input[name="category_tags"]:checked')).map(
    (input) => input.value,
  );
}

function updateInfluencerCategorySummary() {
  if (!influencerCategorySummary) {
    return;
  }
  const selectedTags = getSelectedInfluencerCategoryTags();
  if (selectedTags.length === 0) {
    influencerCategorySummary.textContent = "选择一个或多个分类";
    influencerCategorySummary.classList.add("is-placeholder");
    return;
  }
  influencerCategorySummary.classList.remove("is-placeholder");
  influencerCategorySummary.innerHTML = selectedTags
    .slice(0, 3)
    .map((tag) => `<span class="selected-tag">${escapeHtml(tag)}</span>`)
    .join("");
  if (selectedTags.length > 3) {
    influencerCategorySummary.insertAdjacentHTML(
      "beforeend",
      `<span class="selected-tag more-tag">+${selectedTags.length - 3}</span>`,
    );
  }
}

function closeInfluencerCategoryOptions() {
  if (!influencerCategoryOptionsElement || !influencerCategoryToggle) {
    return;
  }
  influencerCategoryOptionsElement.hidden = true;
  influencerCategoryToggle.setAttribute("aria-expanded", "false");
}

function clearFieldErrors(form) {
  form.querySelectorAll(".field-error").forEach((errorElement) => {
    errorElement.hidden = true;
    errorElement.textContent = "";
  });
  form.querySelectorAll(".field-invalid").forEach((element) => {
    element.classList.remove("field-invalid");
  });
}

function showFieldErrors(form, errors) {
  clearFieldErrors(form);
  Object.entries(errors).forEach(([fieldName, message]) => {
    const errorElement = form.querySelector(`[data-error-for="${fieldName}"]`);
    const fieldElement = form.elements[fieldName];
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.hidden = false;
    }
    fieldElement?.classList.add("field-invalid");
  });
}

function validateInfluencerPayload(payload) {
  const errors = {};
  const profileUrl = String(payload.profile_url || "").trim();
  if (profileUrl) {
    try {
      const parsedUrl = new URL(profileUrl);
      if (!["http:", "https:"].includes(parsedUrl.protocol)) {
        errors.profile_url = "主页链接必须以 http:// 或 https:// 开头";
      } else if (payload.platform !== "其他") {
        const allowedDomains = profileUrlDomainMap[payload.platform] || [];
        const host = parsedUrl.hostname.toLowerCase();
        const isAllowedDomain = allowedDomains.some(
          (domain) => host === domain || host.endsWith(`.${domain}`),
        );
        if (allowedDomains.length > 0 && !isAllowedDomain) {
          errors.profile_url = `当前媒体平台为${payload.platform}，请填写${payload.platform}相关主页链接`;
        }
      }
    } catch {
      errors.profile_url = "主页链接格式不正确";
    }
  }

  const phone = String(payload.phone || "").trim();
  if (phone) {
    let compactPhone = phone.replace(/[\s-]/g, "");
    if (compactPhone.startsWith("+86")) {
      compactPhone = compactPhone.slice(3);
    } else if (compactPhone.startsWith("0086")) {
      compactPhone = compactPhone.slice(4);
    }
    if (!/^1[3-9]\d{9}$/.test(compactPhone)) {
      errors.phone = "请填写 11 位中国大陆手机号，例如 13800138000";
    }
  }

  const email = String(payload.email || "").trim();
  if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    errors.email = "邮箱格式不正确，例如 name@example.com";
  }

  return errors;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatNumber(value) {
  return new Intl.NumberFormat("zh-CN").format(Number(value) || 0);
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  return value.replace("T", " ").slice(0, 16);
}

function getInitials(name) {
  return String(name || "?").slice(0, 1).toUpperCase();
}

function getPrimaryContact(item) {
  return item.wechat || item.phone || item.email || item.other_contact || "-";
}

function setTextParam(params, key, element) {
  const value = element.value.trim();
  if (value) {
    params.set(key, value);
  }
}

function setNumberParam(params, key, element) {
  const value = element.value.trim();
  if (value !== "") {
    params.set(key, value);
  }
}

function renderExternalLink(text, url) {
  const safeText = escapeHtml(text || "-");
  const rawUrl = String(url || "").trim();
  if (!rawUrl) {
    return safeText;
  }

  const href = rawUrl.startsWith("www.") ? `https://${rawUrl}` : rawUrl;
  if (!/^https?:\/\//i.test(href)) {
    return safeText;
  }

  return `<a class="external-text-link" href="${escapeHtml(href)}" target="_blank" rel="noreferrer">${safeText}</a>`;
}

function showMessage(text, type = "success") {
  messageElement.textContent = text;
  messageElement.className = `message ${type}`;
  messageElement.hidden = false;
  window.setTimeout(() => {
    messageElement.hidden = true;
  }, 3200);
}

function clearFormMessage(form) {
  const formMessage = form.querySelector(".form-message");
  clearFieldErrors(form);
  if (!formMessage) {
    return;
  }
  formMessage.hidden = true;
  formMessage.textContent = "";
}

function showFormMessage(form, text) {
  const formMessage = form.querySelector(".form-message");
  if (!formMessage) {
    showMessage(text, "error");
    return;
  }
  formMessage.textContent = text;
  formMessage.hidden = false;
  form.scrollTo({ top: 0, behavior: "smooth" });
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const result = await response.json();
  if (response.status === 401) {
    window.location.href = "/login.html";
    throw new Error("请先登录");
  }
  if (!response.ok) {
    throw new Error(result.message || "请求失败");
  }
  return result;
}

async function loadCurrentUser() {
  const result = await requestJson("/api/auth/me");
  currentUserElement.textContent = result.user.display_name || result.user.username;
}

function renderStats() {
  const totals = dashboardSummary?.totals || {};

  const stats = [
    ["达人总数", totals.influencer_count || 0, "位"],
    ["项目总数", totals.project_count || 0, "个"],
    ["内容总数", totals.content_count || 0, "条"],
    ["总互动量", formatNumber(totals.total_interactions || 0), "次"],
  ];

  statsElement.innerHTML = stats
    .map(
      ([label, value, unit]) => `
        <article class="stat-card">
          <p>${label}</p>
          <strong>${value}<small>${unit}</small></strong>
          ${label === "达人总数" ? `<em>${totals.active_influencer_count || 0} 位正常</em>` : ""}
          ${label === "项目总数" ? `<em>${totals.active_project_count || 0} 个进行中</em>` : ""}
          ${label === "内容总数" ? `<em>${formatNumber(totals.total_views || 0)} 总播放</em>` : ""}
        </article>
      `,
    )
    .join("");
}

function renderCategoryTags(category) {
  const tags = splitCategoryTags(category);
  if (tags.length === 0) {
    return "-";
  }
  const visibleTags = tags.slice(0, 1);
  const hiddenCount = tags.length - visibleTags.length;
  return `
    <span class="table-tag-list" data-tooltip="${escapeHtml(tags.join("、"))}">
      ${visibleTags.map((tag) => `<span class="table-tag">${escapeHtml(tag)}</span>`).join("")}
      ${hiddenCount > 0 ? `<span class="table-tag table-tag-more">+${hiddenCount}</span>` : ""}
    </span>
  `;
}

function renderDashboard() {
  renderStats();
  const summary = dashboardSummary || {
    recent_contents: [],
    sync_distribution: [],
    platform_distribution: [],
  };

  recentContentList.innerHTML = summary.recent_contents.length
    ? summary.recent_contents
        .map(
          (item) => `
            <article class="mini-list-item">
              <div>
                <strong>${escapeHtml(item.title)}</strong>
                <span>${escapeHtml(item.influencer_name)} / ${escapeHtml(item.platform)} / ${escapeHtml(item.published_at || "-")}</span>
              </div>
              <div class="metric-pair">
                <span>播放 ${formatNumber(item.view_count)}</span>
                <span>互动 ${formatNumber(item.interaction_count)}</span>
              </div>
            </article>
          `,
        )
        .join("")
    : `<div class="empty-state compact-empty">暂无内容，去内容库新增第一条吧。</div>`;

  syncStatusList.innerHTML = summary.sync_distribution.length
    ? summary.sync_distribution
        .map(
          (item) => `
            <div class="summary-row">
              <span><i class="dot"></i>${escapeHtml(item.sync_status)}</span>
              <strong>${formatNumber(item.content_count)} 条</strong>
            </div>
          `,
        )
        .join("")
    : `<div class="empty-state compact-empty">暂无同步数据</div>`;

  platformList.innerHTML = summary.platform_distribution.length
    ? summary.platform_distribution
        .map(
          (item) => `
            <div class="summary-row">
              <span><i class="dot blue-dot"></i>${escapeHtml(item.platform)}</span>
              <strong>${formatNumber(item.content_count)} 条 / ${formatNumber(item.view_count)} 播放</strong>
            </div>
          `,
        )
        .join("")
    : `<div class="empty-state compact-empty">暂无平台数据</div>`;
}

function getViewFromHash() {
  const view = window.location.hash.replace("#", "");
  return validViews.has(view) ? view : "dashboard";
}

function switchView(view, shouldUpdateHash = true) {
  if (!validViews.has(view)) {
    view = "dashboard";
  }

  if (shouldUpdateHash && window.location.hash !== `#${view}`) {
    window.location.hash = view;
  }

  activeView = view;
  dashboardSection.hidden = view !== "dashboard";
  influencerSection.hidden = view !== "influencers";
  projectSection.hidden = view !== "projects";
  contentSection.hidden = view !== "contents";
  statsElement.hidden = view !== "dashboard";
  openCreateButton.hidden = view === "dashboard";
  detailSection.hidden = true;
  activeDetail = null;

  document.querySelectorAll(".nav a[data-view]").forEach((link) => {
    link.classList.toggle("active", link.dataset.view === view);
  });

  if (view === "dashboard") {
    loadDashboard();
    return;
  }

  if (view === "projects") {
    openCreateButton.textContent = "+ 新增项目";
    loadProjects();
    return;
  }

  if (view === "contents") {
    openCreateButton.textContent = "+ 新增内容";
    loadProjectOptions();
    loadContents();
    return;
  }

  openCreateButton.textContent = "+ 新增达人";
  loadInfluencers();
}

function renderInfluencers() {
  influencerResultCountElement.textContent = `共 ${influencers.length} 位达人`;

  if (influencers.length === 0) {
    influencerListElement.innerHTML = `
      <tr>
        <td class="empty-state" colspan="9">还没有匹配的达人，可以调整筛选条件或新增达人。</td>
      </tr>
    `;
    renderStats();
    return;
  }

  influencerListElement.innerHTML = influencers
    .map(
      (item) => `
        <tr>
          <td>
            <div class="creator-cell">
              <span class="avatar">${escapeHtml(getInitials(item.name))}</span>
              <div>
                <strong>${renderExternalLink(item.name, item.profile_url)}</strong>
                <small>${escapeHtml(item.account_id || "未填写账号 ID")}</small>
              </div>
            </div>
          </td>
          <td>${escapeHtml(item.platform)}</td>
          <td>${renderCategoryTags(item.category)}</td>
          <td>${formatNumber(item.followers_count)}</td>
          <td>${escapeHtml(item.owner || "-")}</td>
          <td>${escapeHtml(getPrimaryContact(item))}</td>
          <td><span class="status status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
          <td>${formatDate(item.updated_at)}</td>
          <td>
            <div class="table-actions">
              <button class="link-button" type="button" data-type="influencer" data-action="detail" data-id="${item.id}">详情</button>
              <button class="link-button" type="button" data-type="influencer" data-action="edit" data-id="${item.id}">编辑</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");

  renderStats();
}

function renderProjects() {
  projectResultCountElement.textContent = `共 ${projects.length} 个项目`;

  if (projects.length === 0) {
    projectListElement.innerHTML = `
      <tr>
        <td class="empty-state" colspan="8">还没有匹配的项目，可以调整筛选条件或新增项目。</td>
      </tr>
    `;
    renderStats();
    return;
  }

  projectListElement.innerHTML = projects
    .map(
      (item) => `
        <tr>
          <td>
            <div class="creator-cell">
              <span class="avatar">${escapeHtml(getInitials(item.name))}</span>
              <div>
                <strong>${escapeHtml(item.name)}</strong>
                <small>${escapeHtml(item.description || "未填写项目说明")}</small>
              </div>
            </div>
          </td>
          <td>${escapeHtml(item.project_code || "-")}</td>
          <td><span class="status status-${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
          <td>${escapeHtml(item.owner || "-")}</td>
          <td>${escapeHtml(item.start_date || "-")}</td>
          <td>${escapeHtml(item.end_date || "-")}</td>
          <td>${formatDate(item.updated_at)}</td>
          <td>
            <div class="table-actions">
              <button class="link-button" type="button" data-type="project" data-action="detail" data-id="${item.id}">详情</button>
              <button class="link-button" type="button" data-type="project" data-action="edit" data-id="${item.id}">编辑</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");

  renderStats();
}

function renderContents() {
  contentResultCountElement.textContent = `共 ${contents.length} 条内容`;

  if (contents.length === 0) {
    contentListElement.innerHTML = `
      <tr>
        <td class="empty-state" colspan="9">还没有匹配的内容，可以调整筛选条件或新增内容。</td>
      </tr>
    `;
    renderStats();
    return;
  }

  contentListElement.innerHTML = contents
    .map(
      (item) => `
        <tr>
          <td>
            <div class="creator-cell">
              <span class="avatar">${escapeHtml(getInitials(item.title))}</span>
              <div>
                <strong>${renderExternalLink(item.title, item.content_url)}</strong>
                <small>${escapeHtml(item.content_type || "未填写类型")}</small>
              </div>
            </div>
          </td>
          <td>${escapeHtml(item.influencer_name || "-")}</td>
          <td>${escapeHtml(item.platform || "-")}</td>
          <td>${escapeHtml(item.project_name || "-")}</td>
          <td>${escapeHtml(item.published_at || "-")}</td>
          <td>${formatNumber(item.view_count)}</td>
          <td>${formatNumber(item.interaction_count)}</td>
          <td><span class="status status-${escapeHtml(item.sync_status)}">${escapeHtml(item.sync_status || "待同步")}</span></td>
          <td>
            <div class="table-actions">
              <button class="link-button" type="button" data-type="content" data-action="detail" data-id="${item.id}">详情</button>
              <button class="link-button" type="button" data-type="content" data-action="edit" data-id="${item.id}">编辑</button>
              <button class="link-button" type="button" data-type="content" data-action="sync" data-id="${item.id}">同步数据</button>
            </div>
          </td>
        </tr>
      `,
    )
    .join("");

  renderStats();
}

async function loadInfluencers() {
  try {
    const params = new URLSearchParams();
    setTextParam(params, "keyword", influencerKeywordInput);
    if (platformFilter.value) {
      params.set("platform", platformFilter.value);
    }
    setTextParam(params, "category", influencerCategoryFilter);
    setTextParam(params, "owner", influencerOwnerFilter);
    setNumberParam(params, "followers_min", followersMinFilter);
    setNumberParam(params, "followers_max", followersMaxFilter);
    const query = params.toString() ? `?${params.toString()}` : "";
    influencers = await requestJson(`/api/influencers${query}`);
    renderInfluencers();
  } catch (error) {
    influencerResultCountElement.textContent = "加载失败";
    showMessage(error.message, "error");
  }
}

async function loadDashboard() {
  try {
    dashboardSummary = await requestJson("/api/dashboard/summary");
    renderDashboard();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadProjects() {
  try {
    const params = new URLSearchParams();
    setTextParam(params, "keyword", projectKeywordInput);
    if (projectStatusFilter.value) {
      params.set("status", projectStatusFilter.value);
    }
    setTextParam(params, "owner", projectOwnerFilter);
    const query = params.toString() ? `?${params.toString()}` : "";
    projects = await requestJson(`/api/projects${query}`);
    renderProjects();
  } catch (error) {
    projectResultCountElement.textContent = "加载失败";
    showMessage(error.message, "error");
  }
}

async function loadProjectOptions() {
  try {
    projects = await requestJson("/api/projects");
    renderProjectOptions();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadContents() {
  try {
    const params = new URLSearchParams();
    setTextParam(params, "keyword", contentKeywordInput);
    if (contentPlatformFilter.value) {
      params.set("platform", contentPlatformFilter.value);
    }
    if (contentProjectFilter.value) {
      params.set("project_id", contentProjectFilter.value);
    }
    setNumberParam(params, "views_min", viewsMinFilter);
    setNumberParam(params, "views_max", viewsMaxFilter);
    setNumberParam(params, "interactions_min", interactionsMinFilter);
    setNumberParam(params, "interactions_max", interactionsMaxFilter);
    const query = params.toString() ? `?${params.toString()}` : "";
    contents = await requestJson(`/api/contents${query}`);
    renderContents();
  } catch (error) {
    contentResultCountElement.textContent = "加载失败";
    showMessage(error.message, "error");
  }
}

async function loadInfluencerDetail(id) {
  const item = await requestJson(`/api/influencers/${id}`);
  activeDetail = { type: "influencer", id: item.id };
  detailEyebrow.textContent = "INFLUENCER DETAIL";
  detailTitle.textContent = item.name;
  detailContent.innerHTML = `
    ${renderDetailItem("达人名称", item.name)}
    ${renderDetailItem("媒体平台", item.platform)}
    ${renderDetailItem("平台账号 ID", item.account_id)}
    ${renderDetailItem("主页链接", item.profile_url, true)}
    ${renderDetailItem("达人分类", item.category)}
    ${renderDetailItem("粉丝数", formatNumber(item.followers_count))}
    ${renderDetailItem("微信", item.wechat)}
    ${renderDetailItem("手机号", item.phone)}
    ${renderDetailItem("邮箱", item.email)}
    ${renderDetailItem("其他联系方式", item.other_contact)}
    ${renderDetailItem("负责人", item.owner)}
    ${renderDetailItem("状态", item.status)}
    ${renderDetailItem("备注", item.remark)}
    ${renderDetailItem("创建时间", formatDate(item.created_at))}
    ${renderDetailItem("更新时间", formatDate(item.updated_at))}
  `;
  detailSection.hidden = false;
  detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadProjectDetail(id) {
  const item = await requestJson(`/api/projects/${id}`);
  activeDetail = { type: "project", id: item.id };
  detailEyebrow.textContent = "PROJECT DETAIL";
  detailTitle.textContent = item.name;
  detailContent.innerHTML = `
    ${renderDetailItem("项目名称", item.name)}
    ${renderDetailItem("项目编号", item.project_code)}
    ${renderDetailItem("项目状态", item.status)}
    ${renderDetailItem("负责人", item.owner)}
    ${renderDetailItem("开始日期", item.start_date)}
    ${renderDetailItem("结束日期", item.end_date)}
    ${renderDetailItem("项目说明", item.description)}
    ${renderDetailItem("创建时间", formatDate(item.created_at))}
    ${renderDetailItem("更新时间", formatDate(item.updated_at))}
  `;
  detailSection.hidden = false;
  detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function loadContentDetail(id) {
  const item = await requestJson(`/api/contents/${id}`);
  activeDetail = { type: "content", id: item.id };
  detailEyebrow.textContent = "CONTENT DETAIL";
  detailTitle.textContent = item.title;
  detailContent.innerHTML = `
    ${renderDetailItem("内容标题", item.title)}
    ${renderDetailItem("关联达人", item.influencer_name)}
    ${renderDetailItem("关联项目", item.project_name)}
    ${renderDetailItem("媒体平台", item.platform)}
    ${renderDetailItem("内容链接", item.content_url, true)}
    ${renderDetailItem("标准链接", item.canonical_url, true)}
    ${renderDetailItem("平台内容 ID", item.platform_content_id)}
    ${renderDetailItem("发布时间", item.published_at)}
    ${renderDetailItem("内容类型", item.content_type)}
    ${renderDetailItem("负责人", item.owner)}
    ${renderDetailItem("播放量", formatNumber(item.view_count))}
    ${renderDetailItem("点赞", formatNumber(item.like_count))}
    ${renderDetailItem("评论", formatNumber(item.comment_count))}
    ${renderDetailItem("收藏", formatNumber(item.collect_count))}
    ${renderDetailItem("转发", formatNumber(item.share_count))}
    ${renderDetailItem("互动量", formatNumber(item.interaction_count))}
    ${renderDetailItem("同步状态", item.sync_status)}
    ${renderDetailItem("失败原因", item.failed_reason)}
    ${renderDetailItem("备注", item.remark)}
  `;
  detailSection.hidden = false;
  detailSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderDetailItem(label, value, isLink = false) {
  const displayValue = value || "-";
  const safeValue = escapeHtml(displayValue);
  const content =
    isLink && value
      ? `<a href="${safeValue}" target="_blank" rel="noreferrer">${safeValue}</a>`
      : safeValue;
  return `
    <article class="detail-item">
      <span>${label}</span>
      <strong>${content}</strong>
    </article>
  `;
}

function renderContentSelectOptions() {
  contentInfluencerSelect.innerHTML = `
    <option value="">请选择达人</option>
    ${influencers
      .map(
        (item) =>
          `<option value="${item.id}">${escapeHtml(item.name)} / ${escapeHtml(item.platform)}</option>`,
      )
      .join("")}
  `;

  renderProjectOptions();
}

function renderProjectOptions() {
  const projectOptions = projects
    .map(
      (item) =>
        `<option value="${item.id}">${escapeHtml(item.name)}</option>`,
    )
    .join("");

  contentProjectSelect.innerHTML = `
    <option value="">不关联项目</option>
    ${projectOptions}
  `;
  contentProjectFilter.innerHTML = `
    <option value="">全部项目</option>
    <option value="none">未关联项目</option>
    ${projectOptions}
  `;
}

function openCreateDialog() {
  if (activeView === "contents" || activeView === "dashboard") {
    renderContentSelectOptions();
    contentForm.reset();
    clearFormMessage(contentForm);
    contentForm.elements.id.value = "";
    contentForm.elements.status.value = "正常";
    contentForm.elements.content_type.value = "视频";
    contentForm.elements.sync_status.value = "待同步";
    ["view_count", "like_count", "comment_count", "collect_count", "share_count"].forEach((key) => {
      contentForm.elements[key].value = 0;
    });
    contentFormTitle.textContent = "新增内容";
    contentFormEyebrow.textContent = "NEW CONTENT";
    contentForm.querySelector(".submit-button").textContent = "保存内容";
    contentDialog.showModal();
    return;
  }

  if (activeView === "projects") {
    projectForm.reset();
    clearFormMessage(projectForm);
    projectForm.elements.id.value = "";
    projectForm.elements.status.value = "自动判断";
    projectFormTitle.textContent = "新增项目";
    projectFormEyebrow.textContent = "NEW PROJECT";
    projectForm.querySelector(".submit-button").textContent = "保存项目";
    projectDialog.showModal();
    return;
  }

  influencerForm.reset();
  clearFormMessage(influencerForm);
  influencerForm.elements.id.value = "";
  influencerForm.elements.status.value = "正常";
  influencerForm.elements.followers_count.value = 0;
  setInfluencerCategoryTags("");
  closeInfluencerCategoryOptions();
  influencerFormTitle.textContent = "新增达人";
  influencerFormEyebrow.textContent = "NEW INFLUENCER";
  influencerForm.querySelector(".submit-button").textContent = "保存达人";
  influencerDialog.showModal();
}

async function openInfluencerEditDialog(id) {
  try {
    const item = await requestJson(`/api/influencers/${id}`);
    influencerForm.reset();
    clearFormMessage(influencerForm);
    Object.entries(item).forEach(([key, value]) => {
      if (influencerForm.elements[key]) {
        influencerForm.elements[key].value = value ?? "";
      }
    });
    setInfluencerCategoryTags(item.category);
    closeInfluencerCategoryOptions();
    influencerFormTitle.textContent = "编辑达人";
    influencerFormEyebrow.textContent = "EDIT INFLUENCER";
    influencerForm.querySelector(".submit-button").textContent = "保存修改";
    influencerDialog.showModal();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function openProjectEditDialog(id) {
  try {
    const item = await requestJson(`/api/projects/${id}`);
    projectForm.reset();
    clearFormMessage(projectForm);
    Object.entries(item).forEach(([key, value]) => {
      if (projectForm.elements[key]) {
        projectForm.elements[key].value = value ?? "";
      }
    });
    projectForm.elements.status.value = item.status === "已归档" ? "已归档" : "自动判断";
    projectFormTitle.textContent = "编辑项目";
    projectFormEyebrow.textContent = "EDIT PROJECT";
    projectForm.querySelector(".submit-button").textContent = "保存修改";
    projectDialog.showModal();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function openContentEditDialog(id) {
  try {
    await Promise.all([loadInfluencers(), loadProjects()]);
    renderContentSelectOptions();
    const item = await requestJson(`/api/contents/${id}`);
    contentForm.reset();
    clearFormMessage(contentForm);
    Object.entries(item).forEach(([key, value]) => {
      if (contentForm.elements[key]) {
        contentForm.elements[key].value = value ?? "";
      }
    });
    contentFormTitle.textContent = "编辑内容";
    contentFormEyebrow.textContent = "EDIT CONTENT";
    contentForm.querySelector(".submit-button").textContent = "保存修改";
    contentDialog.showModal();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function syncContentData(id, button) {
  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "同步中...";

  try {
    const result = await requestJson(`/api/contents/${id}/sync`, {
      method: "POST",
    });
    await loadContents();
    await loadDashboard();
    if (activeDetail?.type === "content" && activeDetail.id === Number(id)) {
      await loadContentDetail(id);
    }
    showMessage(result.message || "同步成功");
  } catch (error) {
    await loadContents();
    showMessage(`同步失败：${error.message}`, "error");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

function getInfluencerPayload() {
  const formData = new FormData(influencerForm);
  const payload = Object.fromEntries(formData.entries());
  payload.category = formData.getAll("category_tags").join("、");
  delete payload.category_tags;
  payload.followers_count = Number(payload.followers_count || 0);
  return payload;
}

function getProjectPayload() {
  const formData = new FormData(projectForm);
  return Object.fromEntries(formData.entries());
}

function getContentPayload() {
  const formData = new FormData(contentForm);
  const payload = Object.fromEntries(formData.entries());
  ["view_count", "like_count", "comment_count", "collect_count", "share_count"].forEach((key) => {
    payload[key] = Number(payload[key] || 0);
  });
  return payload;
}

document.querySelectorAll(".nav a[data-view]").forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    switchView(link.dataset.view);
  });
});

influencerCategoryToggle?.addEventListener("click", () => {
  const isOpen = influencerCategoryToggle.getAttribute("aria-expanded") === "true";
  influencerCategoryOptionsElement.hidden = isOpen;
  influencerCategoryToggle.setAttribute("aria-expanded", String(!isOpen));
});

influencerCategoryOptionsElement?.addEventListener("change", updateInfluencerCategorySummary);

document.addEventListener("click", (event) => {
  if (!influencerCategoryOptionsElement || influencerCategoryOptionsElement.hidden) {
    return;
  }
  const clickedInside = event.target.closest(".tag-select");
  if (!clickedInside) {
    closeInfluencerCategoryOptions();
  }
});

window.addEventListener("hashchange", () => {
  switchView(getViewFromHash(), false);
});

openCreateButton.addEventListener("click", openCreateDialog);

logoutButton.addEventListener("click", async () => {
  try {
    await requestJson("/api/auth/logout", { method: "POST" });
  } finally {
    window.location.href = "/login.html";
  }
});

document.querySelectorAll(".dialog-close-button").forEach((button) => {
  button.addEventListener("click", () => {
    influencerDialog.close();
    projectDialog.close();
    contentDialog.close();
  });
});

[influencerDialog, projectDialog, contentDialog].forEach((dialog) => {
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      dialog.close();
    }
  });
});

document.querySelector("#close-detail-button").addEventListener("click", () => {
  activeDetail = null;
  detailSection.hidden = true;
});

document.querySelector("#reset-influencer-filter-button").addEventListener("click", () => {
  influencerKeywordInput.value = "";
  platformFilter.value = "";
  influencerCategoryFilter.value = "";
  influencerOwnerFilter.value = "";
  followersMinFilter.value = "";
  followersMaxFilter.value = "";
  loadInfluencers();
});

document.querySelector("#reset-project-filter-button").addEventListener("click", () => {
  projectKeywordInput.value = "";
  projectStatusFilter.value = "";
  projectOwnerFilter.value = "";
  loadProjects();
});

document.querySelector("#reset-content-filter-button").addEventListener("click", () => {
  contentKeywordInput.value = "";
  contentPlatformFilter.value = "";
  contentProjectFilter.value = "";
  viewsMinFilter.value = "";
  viewsMaxFilter.value = "";
  interactionsMinFilter.value = "";
  interactionsMaxFilter.value = "";
  loadContents();
});

influencerKeywordInput.addEventListener("input", () => {
  window.clearTimeout(influencerKeywordInput.searchTimer);
  influencerKeywordInput.searchTimer = window.setTimeout(loadInfluencers, 250);
});

projectKeywordInput.addEventListener("input", () => {
  window.clearTimeout(projectKeywordInput.searchTimer);
  projectKeywordInput.searchTimer = window.setTimeout(loadProjects, 250);
});

contentKeywordInput.addEventListener("input", () => {
  window.clearTimeout(contentKeywordInput.searchTimer);
  contentKeywordInput.searchTimer = window.setTimeout(loadContents, 250);
});

[
  influencerCategoryFilter,
  influencerOwnerFilter,
  followersMinFilter,
  followersMaxFilter,
].forEach((element) => {
  element.addEventListener("input", () => {
    window.clearTimeout(element.searchTimer);
    element.searchTimer = window.setTimeout(loadInfluencers, 250);
  });
});

projectOwnerFilter.addEventListener("input", () => {
  window.clearTimeout(projectOwnerFilter.searchTimer);
  projectOwnerFilter.searchTimer = window.setTimeout(loadProjects, 250);
});

[
  viewsMinFilter,
  viewsMaxFilter,
  interactionsMinFilter,
  interactionsMaxFilter,
].forEach((element) => {
  element.addEventListener("input", () => {
    window.clearTimeout(element.searchTimer);
    element.searchTimer = window.setTimeout(loadContents, 250);
  });
});

platformFilter.addEventListener("change", loadInfluencers);
influencerCategoryFilter.addEventListener("change", loadInfluencers);
projectStatusFilter.addEventListener("change", loadProjects);
contentPlatformFilter.addEventListener("change", loadContents);
contentProjectFilter.addEventListener("change", loadContents);

influencerListElement.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const id = button.dataset.id;
  if (button.dataset.action === "detail") {
    try {
      await loadInfluencerDetail(id);
    } catch (error) {
      showMessage(error.message, "error");
    }
  }
  if (button.dataset.action === "edit") {
    await openInfluencerEditDialog(id);
  }
});

projectListElement.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const id = button.dataset.id;
  if (button.dataset.action === "detail") {
    try {
      await loadProjectDetail(id);
    } catch (error) {
      showMessage(error.message, "error");
    }
  }
  if (button.dataset.action === "edit") {
    await openProjectEditDialog(id);
  }
});

contentListElement.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  const id = button.dataset.id;
  if (button.dataset.action === "detail") {
    try {
      await loadContentDetail(id);
    } catch (error) {
      showMessage(error.message, "error");
    }
  }
  if (button.dataset.action === "edit") {
    await openContentEditDialog(id);
  }
  if (button.dataset.action === "sync") {
    await syncContentData(id, button);
  }
});

influencerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = influencerForm.querySelector('button[type="submit"]');
  const payload = getInfluencerPayload();
  const isEdit = Boolean(payload.id);
  const url = isEdit ? `/api/influencers/${payload.id}` : "/api/influencers";
  const method = isEdit ? "PUT" : "POST";

  submitButton.disabled = true;
  submitButton.textContent = "保存中...";
  clearFormMessage(influencerForm);

  const fieldErrors = validateInfluencerPayload(payload);
  if (Object.keys(fieldErrors).length > 0) {
    showFieldErrors(influencerForm, fieldErrors);
    showFormMessage(influencerForm, "请检查标红字段后再保存");
    submitButton.disabled = false;
    submitButton.textContent = isEdit ? "保存修改" : "保存达人";
    return;
  }

  try {
    const result = await requestJson(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    await loadInfluencers();
    await loadDashboard();
    if (activeDetail?.type === "influencer" && activeDetail.id === result.id) {
      await loadInfluencerDetail(result.id);
    }
    influencerDialog.close();
    showMessage(isEdit ? `已更新达人：${result.name}` : `已添加达人：${result.name}`);
  } catch (error) {
    showFormMessage(influencerForm, error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = isEdit ? "保存修改" : "保存达人";
  }
});

projectForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = projectForm.querySelector('button[type="submit"]');
  const payload = getProjectPayload();
  const isEdit = Boolean(payload.id);
  const url = isEdit ? `/api/projects/${payload.id}` : "/api/projects";
  const method = isEdit ? "PUT" : "POST";

  submitButton.disabled = true;
  submitButton.textContent = "保存中...";
  clearFormMessage(projectForm);

  try {
    const result = await requestJson(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    await loadProjects();
    await loadDashboard();
    if (activeDetail?.type === "project" && activeDetail.id === result.id) {
      await loadProjectDetail(result.id);
    }
    projectDialog.close();
    showMessage(isEdit ? `已更新项目：${result.name}` : `已添加项目：${result.name}`);
  } catch (error) {
    showFormMessage(projectForm, error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = isEdit ? "保存修改" : "保存项目";
  }
});

contentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = contentForm.querySelector('button[type="submit"]');
  const payload = getContentPayload();
  const isEdit = Boolean(payload.id);
  const url = isEdit ? `/api/contents/${payload.id}` : "/api/contents";
  const method = isEdit ? "PUT" : "POST";

  submitButton.disabled = true;
  submitButton.textContent = "保存中...";
  clearFormMessage(contentForm);

  try {
    const result = await requestJson(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    await loadContents();
    await loadDashboard();
    if (activeDetail?.type === "content" && activeDetail.id === result.id) {
      await loadContentDetail(result.id);
    }
    contentDialog.close();
    showMessage(isEdit ? `已更新内容：${result.title}` : `已添加内容：${result.title}`);
  } catch (error) {
    showFormMessage(contentForm, error.message);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = isEdit ? "保存修改" : "保存内容";
  }
});

renderInfluencerCategoryOptions();
renderInfluencerCategoryFilterOptions();

loadCurrentUser()
  .then(() => {
    switchView(getViewFromHash(), false);
  })
  .catch(() => {
    window.location.href = "/login.html";
  });
