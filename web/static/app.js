// API Base URL
const API_BASE = window.location.origin;

// State
let currentStyle = '励志';
let currentTemplate = 'default';
let currentRatio = '16:9';
let currentTTSProvider = 'moss';
let currentSubtitleStyle = 'impact';
let currentMode = 'short';  // 'normal' or 'short'
let currentDuration = 30;
let currentTransition = 'fast';  // 'normal', 'fast', 'cinematic'
let energyAnalysis = null;  // 能量分析结果
let uploadedFile = null;
let userAssets = [];
let outputId = null;
let previewTemplate = null;
let wsConnection = null;

// 文案和TTS状态（确认后用于生产）
let confirmedNarrative = null;  // 用户确认的文案 { title_text, narration_script }
let confirmedTTSParams = null;   // 用户确认的TTS参数 { voice, tts_provider, tts_instruction }
let narrativeGenerated = false;  // 是否已生成文案
let ttsPreviewed = false;        // 是否已预览TTS

// Voice State
let currentVoiceId = '';
let currentSpeedTemplate = 'speed_normal';
let currentPauseTemplate = 'pause_normal';
let currentEmotionTemplate = 'emotion_warm';
let voiceRecommendation = null;

// ── 模板预览视频映射 ──
const TEMPLATE_PREVIEWS = {
    default: {
        title: '默认模板',
        desc: '标准情感视频，适合各类场景。动态转场、标准字幕样式。',
        video: '/web/static/previews/default.mp4'
    },
    cinematic: {
        title: '电影风格',
        desc: '大标题 + 深色调，专业叙事风格。适合故事类内容。',
        video: '/web/static/previews/cinematic.mp4'
    },
    minimal: {
        title: '极简风格',
        desc: '简洁字幕 + 浅色调。适合治愈、文艺类内容。',
        video: '/web/static/previews/minimal.mp4'
    },
    neon: {
        title: '霓虹风格',
        desc: '发光字幕 + 暗色调。适合夜景、科技类内容。',
        video: '/web/static/previews/neon.mp4'
    }
};

// ── 模板预览 ──
function showTemplatePreview(template) {
    previewTemplate = template;
    const preview = TEMPLATE_PREVIEWS[template];

    document.getElementById('previewTitle').textContent = preview.title;
    document.getElementById('previewDesc').textContent = preview.desc;

    const video = document.getElementById('previewVideo');
    video.src = preview.video;

    // 如果视频加载失败，使用静态图片作为背景
    video.onerror = function() {
        video.poster = preview.fallback;
        video.loop = true;
    };

    document.getElementById('previewModal').classList.add('active');
}

function closePreviewModal() {
    document.getElementById('previewModal').classList.remove('active');
    document.getElementById('previewVideo').pause();
    previewTemplate = null;
}

function applyPreviewTemplate() {
    if (previewTemplate) {
        selectTemplate(previewTemplate);
    }
    closePreviewModal();
}

// ── 字幕样式选择 ──
function selectSubtitleStyle(style) {
    currentSubtitleStyle = style;
    document.querySelectorAll('.style-option').forEach(opt => opt.classList.remove('active'));
    document.querySelector(`.style-option[data-style="${style}"]`).classList.add('active');
    updateSubtitleDemo();

    // 触发动画效果
    const previewText = document.querySelector(`.style-option[data-style="${style}"] .style-preview-text`);
    if (previewText) {
        previewText.style.animation = 'none';
        setTimeout(() => {
            previewText.style.animation = '';
        }, 10);
    }
}

// ── API 配置保存 ──
async function saveApiConfig() {
    const dashscopeKey = document.getElementById('dashscopeKey').value.trim();
    const mossKey = document.getElementById('mossKey').value.trim();
    const pexelsKey = document.getElementById('pexelsKey').value.trim();
    const pixabayKey = document.getElementById('pixabayKey').value.trim();

    try {
        const response = await fetch(`${API_BASE}/api/config/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                DASHSCOPE_API_KEY: dashscopeKey,
                MOSS_API_KEY: mossKey,
                PEXELS_API_KEY: pexelsKey,
                PIXABAY_API_KEY: pixabayKey,
            })
        });

        const data = await response.json();

        if (data.success) {
            const statusEl = document.getElementById('configStatus');
            statusEl.style.display = 'block';
            statusEl.className = 'status-message success';
            statusEl.textContent = '✓ 配置已保存并持久化';
            setTimeout(() => statusEl.style.display = 'none', 3000);
        } else {
            showError(data.error || '配置保存失败');
        }
    } catch (err) {
        showError('配置保存失败: ' + err.message);
    }
}

// ── 加载已保存的配置 ──
async function loadSavedConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config/load`);
        const data = await response.json();

        if (data.success && data.config) {
            document.getElementById('dashscopeKey').value = data.config.DASHSCOPE_API_KEY || '';
            document.getElementById('mossKey').value = data.config.MOSS_API_KEY || '';
            document.getElementById('pexelsKey').value = data.config.PEXELS_API_KEY || '';
            document.getElementById('pixabayKey').value = data.config.PIXABAY_API_KEY || '';
        }
    } catch (err) {
        console.log('加载配置失败:', err);
    }
}

// 页面加载时加载配置
loadSavedConfig();

// TTS Provider change
document.getElementById('ttsProvider').addEventListener('change', function() {
    currentTTSProvider = this.value;
    const cosyvoiceSettings = document.getElementById('cosyvoiceSettings');
    const mossSettings = document.getElementById('mossSettings');
    if (this.value === 'cosyvoice') {
        cosyvoiceSettings.style.display = 'flex';
        mossSettings.style.display = 'none';
    } else if (this.value === 'moss') {
        cosyvoiceSettings.style.display = 'none';
        mossSettings.style.display = 'flex';
        // 加载音色推荐
        loadVoiceRecommendation();
    } else {
        cosyvoiceSettings.style.display = 'none';
        mossSettings.style.display = 'none';
    }
});

// Template Selection
function selectTemplate(template) {
    currentTemplate = template;
    document.querySelectorAll('.template-card').forEach(card => card.classList.remove('active'));
    document.querySelector(`.template-card[data-template="${template}"]`).classList.add('active');
    updateSubtitleDemo();
}

// Ratio Selection
function selectRatio(ratio) {
    currentRatio = ratio;
    document.querySelectorAll('.ratio-option').forEach(opt => opt.classList.remove('active'));
    document.querySelector(`.ratio-option[data-ratio="${ratio}"]`).classList.add('active');
    updateSubtitleDemo();
}

// Mode Selection
function selectMode(mode) {
    currentMode = mode;
    document.querySelectorAll('.mode-option').forEach(opt => opt.classList.remove('active'));
    document.querySelector(`.mode-option[data-mode="${mode}"]`).classList.add('active');

    // 自动配置短视频模式参数
    if (mode === 'short') {
        currentDuration = 30;
        currentTransition = 'fast';
        document.getElementById('durationSlider').value = 30;
        updateDurationDisplay();
        selectTransition('fast');

        // 显示时长控制
        document.getElementById('durationControl').style.display = 'block';
        document.getElementById('transitionNote').style.display = 'block';
    } else {
        currentDuration = 120;
        currentTransition = 'normal';
        selectTransition('normal');

        // 隐藏时长控制（标准模式不限制时长）
        document.getElementById('durationControl').style.display = 'none';
        document.getElementById('transitionNote').style.display = 'none';
    }
}

// Duration Slider
function updateDurationDisplay() {
    const slider = document.getElementById('durationSlider');
    currentDuration = parseInt(slider.value);
    document.getElementById('durationValue').textContent = `${currentDuration}秒`;
    document.querySelector('.duration-current').textContent = `${currentDuration}s`;
}

// Transition Selection
function selectTransition(transition) {
    currentTransition = transition;
    document.querySelectorAll('.transition-option').forEach(opt => opt.classList.remove('active'));
    document.querySelector(`.transition-option[data-transition="${transition}"]`).classList.add('active');
}

// Update Subtitle Demo
function updateSubtitleDemo() {
    const frame = document.getElementById('subtitleDemoFrame');
    const subtitle = document.getElementById('demoSubtitle');
    const videoBg = frame.querySelector('.demo-video-bg');

    // Update frame aspect ratio
    if (currentRatio === '9:16') {
        frame.classList.add('ratio-vertical');
    } else {
        frame.classList.remove('ratio-vertical');
    }

    // Update background based on template
    videoBg.className = 'demo-video-bg template-' + currentTemplate;

    // Update subtitle style
    subtitle.className = 'demo-subtitle style-' + currentSubtitleStyle;

    // For minimal template, use dark subtitle
    if (currentTemplate === 'minimal') {
        subtitle.style.color = '#1a1a1a';
        if (currentSubtitleStyle === 'neon') {
            subtitle.style.color = '#0066ff';
            subtitle.style.textShadow = '0 0 8px #0066ff';
        }
    } else {
        subtitle.style.color = '';
    }

    // Update info display
    const templateNames = {
        'default': '默认',
        'cinematic': '电影',
        'minimal': '极简',
        'neon': '霓虹'
    };
    document.getElementById('demoTemplateInfo').textContent = templateNames[currentTemplate] || '默认';
    document.getElementById('demoRatioInfo').textContent = currentRatio === '9:16' ? '9:16 竖屏' : '16:9 横屏';

    // Update subtitle size based on ratio
    const sizeMap = {
        '16:9': { 'impact': '48px', 'minimal': '32px', 'neon': '40px', 'cinematic': '36px', 'typewriter': '34px', 'bounce': '42px', 'card': '36px' },
        '9:16': { 'impact': '64px', 'minimal': '42px', 'neon': '52px', 'cinematic': '48px', 'typewriter': '46px', 'bounce': '56px', 'card': '48px' }
    };
    document.getElementById('demoSizeInfo').textContent = sizeMap[currentRatio][currentSubtitleStyle] || '48px';
}

// File Upload - BGM
let bgmFileLocalUrl = null;

document.getElementById('bgm').addEventListener('change', async function(e) {
    const file = e.target.files[0];
    if (!file) return;

    const uploadArea = document.getElementById('bgmUploadArea');
    const uploadText = document.getElementById('bgmUploadText');
    const audioPlayer = document.getElementById('audioPlayer');
    const bgmAudio = document.getElementById('bgmAudio');

    uploadText.textContent = `上传中: ${file.name}...`;

    // 创建本地预览 URL
    if (bgmFileLocalUrl) {
        URL.revokeObjectURL(bgmFileLocalUrl);
    }
    bgmFileLocalUrl = URL.createObjectURL(file);

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            uploadedFile = data;
            uploadArea.style.display = 'none';
            audioPlayer.style.display = 'block';

            // 设置音频源为本地预览
            bgmAudio.src = bgmFileLocalUrl;
            bgmAudio.load();

            // 更新时长显示
            bgmAudio.addEventListener('loadedmetadata', function() {
                document.getElementById('audioDuration').textContent = formatTime(bgmAudio.duration);
            });

            // 短视频模式下触发能量分析预览
            if (currentMode === 'short') {
                analyzeEnergyPreview(data.file_path);
            }

            // 自动触发文案生成（如果已输入主题）
            onBgmUploaded();
        } else {
            showError(data.error || '上传失败');
            uploadArea.style.display = 'block';
            audioPlayer.style.display = 'none';
            uploadText.textContent = '点击上传 MP3 / WAV / M4A';
        }
    } catch (err) {
        showError('上传失败: ' + err.message);
        uploadArea.style.display = 'block';
        audioPlayer.style.display = 'none';
        uploadText.textContent = '点击上传 MP3 / WAV / M4A';
    }
});

// 音频播放控制
function togglePlayPause() {
    const audio = document.getElementById('bgmAudio');
    const playIcon = document.getElementById('playIcon');
    const pauseIcon = document.getElementById('pauseIcon');

    if (audio.paused) {
        audio.play();
        playIcon.style.display = 'none';
        pauseIcon.style.display = 'block';
    } else {
        audio.pause();
        playIcon.style.display = 'block';
        pauseIcon.style.display = 'none';
    }
}

// 更新进度条
document.getElementById('bgmAudio').addEventListener('timeupdate', function() {
    const audio = this;
    const progressFill = document.getElementById('audioProgressFill');
    const currentTimeEl = document.getElementById('audioCurrentTime');

    if (audio.duration) {
        const progress = (audio.currentTime / audio.duration) * 100;
        progressFill.style.width = progress + '%';
        currentTimeEl.textContent = formatTime(audio.currentTime);
    }
});

// 音频结束时重置
document.getElementById('bgmAudio').addEventListener('ended', function() {
    document.getElementById('playIcon').style.display = 'block';
    document.getElementById('pauseIcon').style.display = 'none';
});

// 点击进度条跳转
function seekAudio(event) {
    const audio = document.getElementById('bgmAudio');
    const progressBar = document.getElementById('audioProgressBar');
    const rect = progressBar.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;
    audio.currentTime = percent * audio.duration;
}

// 设置音量
function setAudioVolume(value) {
    const audio = document.getElementById('bgmAudio');
    audio.volume = value / 100;
}

// 移除音频文件
function removeBgmFile() {
    const audio = document.getElementById('bgmAudio');
    audio.pause();
    audio.src = '';

    if (bgmFileLocalUrl) {
        URL.revokeObjectURL(bgmFileLocalUrl);
        bgmFileLocalUrl = null;
    }

    uploadedFile = null;
    energyAnalysis = null;
    document.getElementById('bgm').value = '';
    document.getElementById('audioPlayer').style.display = 'none';
    document.getElementById('bgmUploadArea').style.display = 'block';
    document.getElementById('bgmUploadText').textContent = '点击上传 MP3 / WAV / M4A';
    document.getElementById('playIcon').style.display = 'block';
    document.getElementById('pauseIcon').style.display = 'none';
    document.getElementById('audioProgressFill').style.width = '0%';
    document.getElementById('audioCurrentTime').textContent = '0:00';
    document.getElementById('audioDuration').textContent = '0:00';

    // 隐藏能量预览
    document.getElementById('energyPreviewSection').style.display = 'none';
}

// ── 能量分析预览 ──

async function analyzeEnergyPreview(bgmPath) {
    const energySection = document.getElementById('energyPreviewSection');
    const energyStatus = document.getElementById('energyStatus');

    energySection.style.display = 'block';
    energyStatus.textContent = '分析中...';
    energyStatus.classList.remove('analyzed');

    try {
        const response = await fetch(`${API_BASE}/api/music/energy-preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                bgm_path: bgmPath,
                duration_limit: currentDuration,
                mode: currentMode
            })
        });

        const data = await response.json();
        if (data.success) {
            energyAnalysis = data.analysis;
            displayEnergyPreview(data.analysis);
        } else {
            energyStatus.textContent = '分析失败';
            // 显示默认估计值
            displayDefaultEnergyEstimate();
        }
    } catch (err) {
        console.error('能量分析失败:', err);
        energyStatus.textContent = '分析失败';
        displayDefaultEnergyEstimate();
    }
}

function displayEnergyPreview(analysis) {
    const energyStatus = document.getElementById('energyStatus');
    energyStatus.textContent = '已分析';
    energyStatus.classList.add('analyzed');

    // 根据能量级别估算片段数
    const duration = analysis.duration || currentDuration;
    const energyLevel = analysis.energy_level || 'medium';

    let segmentEstimate;
    let highEnergyEstimate;
    let fastCutDuration;

    if (currentMode === 'short') {
        // 短视频模式：更细致的分段
        if (energyLevel === 'high') {
            segmentEstimate = Math.round(duration / 1.8);  // 1.5-2s 每段
            highEnergyEstimate = Math.round(segmentEstimate * 0.6);
            fastCutDuration = '1.5-2s';
        } else if (energyLevel === 'medium') {
            segmentEstimate = Math.round(duration / 2.5);  // 2-3s 每段
            highEnergyEstimate = Math.round(segmentEstimate * 0.3);
            fastCutDuration = '2-3s';
        } else {
            segmentEstimate = Math.round(duration / 4);  // 3-5s 每段
            highEnergyEstimate = Math.round(segmentEstimate * 0.15);
            fastCutDuration = '3-5s';
        }
    } else {
        // 标准模式：默认分段
        segmentEstimate = 7;
        highEnergyEstimate = 2;
        fastCutDuration = '0.3-0.5s';
    }

    document.getElementById('segmentCountEstimate').textContent = `${segmentEstimate}-${segmentEstimate + 2}`;
    document.getElementById('highEnergySegments').textContent = `${highEnergyEstimate}-${highEnergyEstimate + 1}`;
    document.getElementById('fastCutDuration').textContent = fastCutDuration;

    // 绘制能量条
    renderEnergyBar(analysis);
}

function displayDefaultEnergyEstimate() {
    // 短视频模式的默认估计
    if (currentMode === 'short') {
        document.getElementById('segmentCountEstimate').textContent = '15-20';
        document.getElementById('highEnergySegments').textContent = '6-8';
        document.getElementById('fastCutDuration').textContent = '1.5-2s';
    } else {
        document.getElementById('segmentCountEstimate').textContent = '7';
        document.getElementById('highEnergySegments').textContent = '2-3';
        document.getElementById('fastCutDuration').textContent = '0.3-0.5s';
    }
}

function renderEnergyBar(analysis) {
    const peaksContainer = document.getElementById('energyPeaks');
    peaksContainer.innerHTML = '';

    // 根据分析结果绘制峰值标记
    if (analysis.energy_peaks && analysis.energy_peaks.length > 0) {
        const duration = analysis.duration || 30;
        analysis.energy_peaks.forEach(peak => {
            const marker = document.createElement('div');
            marker.className = 'peak-marker';
            marker.style.left = `${(peak.time / duration) * 100}%`;
            marker.style.height = `${peak.intensity * 100}%`;
            peaksContainer.appendChild(marker);
        });
    }
}

// 格式化时间
function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// User Asset Upload
document.getElementById('userAsset').addEventListener('change', async function(e) {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    document.getElementById('userAssetFileName').textContent = `上传中...`;

    for (const file of files) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_BASE}/api/user-assets/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                userAssets.push({
                    id: data.asset_id,
                    path: data.asset_path,
                    type: data.asset_type,
                    name: file.name,
                    duration: data.duration || 0
                });
                renderUserAssets();
            }
        } catch (err) {
            console.error('上传失败:', err);
        }
    }

    document.getElementById('userAssetFileName').textContent = `已上传 ${userAssets.length} 个素材`;
    document.getElementById('analyzeBtn').disabled = userAssets.length === 0;
});

// Render User Assets
function renderUserAssets() {
    const container = document.getElementById('userAssetsList');
    container.innerHTML = '';

    for (const asset of userAssets) {
        const item = document.createElement('div');
        item.className = 'asset-item';
        item.dataset.id = asset.id;

        if (asset.type === 'image') {
            item.innerHTML = `
                <img src="file://${asset.path}" alt="${asset.name}">
                <div class="asset-remove" onclick="removeAsset('${asset.id}')">×</div>
            `;
        } else {
            item.innerHTML = `
                <video src="file://${asset.path}" muted></video>
                <div class="asset-remove" onclick="removeAsset('${asset.id}')">×</div>
            `;
        }

        container.appendChild(item);
    }
}

// Remove Asset
function removeAsset(assetId) {
    userAssets = userAssets.filter(a => a.id !== assetId);
    renderUserAssets();
    document.getElementById('userAssetFileName').textContent = userAssets.length > 0
        ? `已上传 ${userAssets.length} 个素材`
        : '未选择文件';
    document.getElementById('analyzeBtn').disabled = userAssets.length === 0;
}

// Analyze User Assets
async function analyzeUserAssets() {
    if (userAssets.length === 0) return;

    const theme = document.getElementById('theme').value.trim() || '视频主题';
    const assetPaths = userAssets.map(a => a.path);

    try {
        const response = await fetch(`${API_BASE}/api/user-assets/generate-script`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                asset_paths: assetPaths,
                theme: theme
            })
        });

        const data = await response.json();

        if (data.success) {
            document.getElementById('analysisResult').style.display = 'block';
            document.getElementById('analysisResult').innerHTML = `
                <h4>AI 分析结果</h4>
                <p>${data.script}</p>
                <p style="margin-top: 8px; color: rgba(255,255,255,0.6);">
                    分析了 ${data.analyses_count} 个素材
                </p>
            `;
        } else {
            showError(data.error || '分析失败');
        }
    } catch (err) {
        showError('分析失败: ' + err.message);
    }
}

// ── 文案预览 ──

let narrativeData = null;  // 保存文案数据
let ttsPreviewData = null;  // TTS 预览数据
let ttsPreviewAudioUrl = null;  // TTS 预览音频 URL

// 上传音乐后自动触发文案生成
function onBgmUploaded() {
    const theme = document.getElementById('theme').value.trim();
    if (theme && uploadedFile) {
        // 自动生成文案
        previewNarrative();
    }
}

async function previewNarrative() {
    const theme = document.getElementById('theme').value;
    if (!theme) {
        showError('请输入视频主题');
        return;
    }

    if (!uploadedFile) {
        showError('请先上传背景音乐');
        return;
    }

    const previewBtn = document.querySelector('.btn-preview');
    previewBtn.textContent = '生成中...';
    previewBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/api/narrative/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                theme: theme,
                bgm_path: uploadedFile.file_path,
                style: currentStyle
            })
        });

        const data = await response.json();
        if (data.success) {
            narrativeData = data.narrative;
            narrativeGenerated = true;
            displayNarrativePreview(data.narrative, data.analysis);
        } else {
            showError(data.error || '文案生成失败');
        }
    } catch (err) {
        showError('请求失败: ' + err.message);
    } finally {
        previewBtn.textContent = '生成文案';
        previewBtn.disabled = false;
    }
}

function displayNarrativePreview(narrative, analysis) {
    // 显示预览区域
    document.getElementById('narrativePreview').style.display = 'block';

    // 填充内容
    document.getElementById('titleTextPreview').value = narrative.title_text || '';
    document.getElementById('narrationScriptPreview').value = narrative.narration_script || '';

    // 显示分析信息
    const info = document.getElementById('narrativeInfo');
    info.innerHTML = `
        音乐时长: ${analysis.duration?.toFixed(1) || 0}s |
        推荐风格: ${analysis.recommended_style || '自动'} |
        能量峰值: ${analysis.energy_peaks?.length || 0} 个
    `;

    // 显示确认按钮
    document.getElementById('confirmNarrativeBtn').style.display = 'inline-block';

    // 初始化 TTS 预览控件
    initTTSPreviewControls();

    // 显示 TTS 预览区域
    document.getElementById('ttsPreviewSection').style.display = 'block';
}

// 确认文案（用户编辑后点击确认）
function confirmNarrative() {
    const titleText = document.getElementById('titleTextPreview').value.trim();
    const narrationScript = document.getElementById('narrationScriptPreview').value.trim();

    if (!narrationScript) {
        showError('请输入旁白文案');
        return;
    }

    confirmedNarrative = {
        title_text: titleText,
        narration_script: narrationScript
    };

    // 更新UI显示已确认
    document.getElementById('confirmNarrativeBtn').textContent = '已确认 ✓';
    document.getElementById('confirmNarrativeBtn').disabled = true;
    document.getElementById('confirmNarrativeBtn').classList.add('confirmed');

    // 显示TTS预览区域
    document.getElementById('ttsPreviewSection').style.display = 'block';

    addLog('文案已确认，可以生成语音预览', 'success');
}

// 获取最终确认的文案（如果用户没有确认，使用编辑框内容）
function getFinalNarrative() {
    if (confirmedNarrative) {
        return confirmedNarrative;
    }
    // 如果没有确认，使用编辑框当前内容
    return {
        title_text: document.getElementById('titleTextPreview')?.value || narrativeData?.title_text,
        narration_script: document.getElementById('narrationScriptPreview')?.value || narrativeData?.narration_script,
    };
}

// ── TTS 预览 ──

function initTTSPreviewControls() {
    // 填充音色选择
    populateTTSPreviewVoices();

    // 初始化指令预览
    updateTTSPreviewInstruction();
}

function populateTTSPreviewVoices() {
    const select = document.getElementById('ttsPreviewVoice');

    // 如果有推荐音色，使用推荐音色
    if (voiceRecommendation && voiceRecommendation.recommended_voice) {
        select.innerHTML = `<option value="${voiceRecommendation.recommended_voice.voice_id}">${voiceRecommendation.recommended_voice.description}</option>`;
        voiceRecommendation.alternative_voices.forEach(v => {
            select.innerHTML += `<option value="${v.voice_id}">${v.description}</option>`;
        });
    } else {
        // 使用当前选中的音色
        select.innerHTML = `<option value="${currentVoiceId || 'zh_female_chengnian'}">当前音色</option>`;
    }
}

function updateTTSPreviewVoice() {
    updateTTSPreviewInstruction();
}

function updateTTSPreviewInstruction() {
    const voiceSelect = document.getElementById('ttsPreviewVoice');
    const speedSelect = document.getElementById('ttsPreviewSpeed');
    const emotionSelect = document.getElementById('ttsPreviewEmotion');

    const voiceId = voiceSelect?.value || currentVoiceId;
    const speedTemplate = speedSelect?.value || 'speed_normal';
    const emotionTemplate = emotionSelect?.value || 'emotion_warm';

    // 构建指令文本
    const speedText = {
        speed_normal: '语速适中',
        speed_fast: '语速较快',
        speed_slow: '语速缓慢'
    };

    const emotionText = {
        emotion_warm: '温暖治愈',
        emotion_energetic: '充满激情',
        emotion_calm: '平和舒缓',
        emotion_serious: '沉稳有力',
        emotion_lively: '活泼俏皮'
    };

    // 从音色库获取音色描述
    let voiceDesc = '成年女声';
    if (voiceRecommendation) {
        const voice = voiceRecommendation.recommended_voice;
        if (voice && voice.voice_id === voiceId) {
            voiceDesc = voice.description;
        } else {
            const alt = voiceRecommendation.alternative_voices.find(v => v.voice_id === voiceId);
            if (alt) voiceDesc = alt.description;
        }
    }

    const instruction = `${voiceDesc}，${speedText[speedTemplate]}，${emotionText[emotionTemplate]}`;
    document.getElementById('ttsPreviewInstructionText').textContent = instruction;
}

async function generateTTSPreview() {
    const narrative = getFinalNarrative();
    const text = narrative.narration_script;

    if (!text) {
        showError('请先生成或确认文案');
        return;
    }

    const btn = document.querySelector('.btn-tts-generate');
    btn.textContent = '生成中...';
    btn.disabled = true;

    const voiceSelect = document.getElementById('ttsPreviewVoice');
    const speedSelect = document.getElementById('ttsPreviewSpeed');
    const emotionSelect = document.getElementById('ttsPreviewEmotion');

    // 保存当前预览参数
    const previewParams = {
        voice: voiceSelect?.value || currentVoiceId,
        tts_provider: currentTTSProvider,
        tts_instruction: document.getElementById('ttsPreviewInstructionText').textContent
    };

    try {
        const response = await fetch(`${API_BASE}/api/tts/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text.substring(0, 200),  // 只预览前 200 字
                voice: previewParams.voice,
                tts_provider: previewParams.tts_provider,
                tts_instruction: previewParams.tts_instruction
            })
        });

        const data = await response.json();
        if (data.success) {
            ttsPreviewData = data;
            ttsPreviewed = true;
            displayTTSPreview(data, previewParams);
        } else {
            showError(data.error || 'TTS 生成失败');
        }
    } catch (err) {
        showError('请求失败: ' + err.message);
    } finally {
        btn.textContent = '生成语音预览';
        btn.disabled = false;
    }
}

function displayTTSPreview(data, params) {
    // 显示播放器
    document.getElementById('ttsPlayer').style.display = 'block';

    // 设置音频源
    const audio = document.getElementById('ttsPreviewAudio');
    audio.src = data.preview_url;

    // 设置音频事件监听
    audio.onloadedmetadata = function() {
        document.getElementById('ttsDuration').textContent = formatTime(audio.duration);
    };

    audio.ontimeupdate = function() {
        const progressFill = document.getElementById('ttsProgressFill');
        const currentTimeEl = document.getElementById('ttsCurrentTime');

        const progress = (audio.currentTime / audio.duration) * 100;
        progressFill.width = `${progress}%`;
        currentTimeEl.textContent = formatTime(audio.currentTime);
    };

    audio.onended = function() {
        document.getElementById('ttsPlayIcon').style.display = 'block';
        document.getElementById('ttsPauseIcon').style.display = 'none';
    };

    // 更新音色信息
    const voiceSelect = document.getElementById('ttsPreviewVoice');
    document.getElementById('ttsVoiceInfo').textContent = voiceSelect?.options[voiceSelect.selectedIndex]?.text || '当前音色';
    document.getElementById('ttsInstructionInfo').textContent = params.tts_instruction;

    // 保存预览参数（用于最终生产）
    confirmedTTSParams = params;

    // 显示确认按钮
    document.getElementById('confirmTTSBtn').style.display = 'inline-block';

    // 显示调整区域
    document.getElementById('ttsAdjustSection').style.display = 'block';
}

// 确认TTS参数
function confirmTTS() {
    const voiceSelect = document.getElementById('ttsPreviewVoice');
    const speedSelect = document.getElementById('ttsPreviewSpeed');
    const emotionSelect = document.getElementById('ttsPreviewEmotion');

    confirmedTTSParams = {
        voice: voiceSelect?.value || currentVoiceId,
        tts_provider: currentTTSProvider,
        tts_instruction: document.getElementById('ttsPreviewInstructionText').textContent
    };

    // 更新UI显示已确认
    document.getElementById('confirmTTSBtn').textContent = '已确认 ✓';
    document.getElementById('confirmTTSBtn').disabled = true;
    document.getElementById('confirmTTSBtn').classList.add('confirmed');

    // 同步到主设置区域
    document.getElementById('mossInstruction').value = confirmedTTSParams.tts_instruction;

    addLog('语音参数已确认，可以开始生产', 'success');

    // 启用生产按钮
    document.getElementById('produceBtn').disabled = false;
}

function toggleTTSPlayPause() {
    const audio = document.getElementById('ttsPreviewAudio');
    const playIcon = document.getElementById('ttsPlayIcon');
    const pauseIcon = document.getElementById('ttsPauseIcon');

    if (audio.paused) {
        audio.play();
        playIcon.style.display = 'none';
        pauseIcon.style.display = 'block';
    } else {
        audio.pause();
        playIcon.style.display = 'block';
        pauseIcon.style.display = 'none';
    }
}

// TTS 音频时间更新
document.addEventListener('DOMContentLoaded', function() {
    const audio = document.getElementById('ttsPreviewAudio');
    if (audio) {
        audio.addEventListener('timeupdate', function() {
            const progressFill = document.getElementById('ttsProgressFill');
            const currentTimeEl = document.getElementById('ttsCurrentTime');

            const progress = (audio.currentTime / audio.duration) * 100;
            progressFill.style.width = `${progress}%`;
            currentTimeEl.textContent = formatTime(audio.currentTime);
        });

        audio.addEventListener('ended', function() {
            document.getElementById('ttsPlayIcon').style.display = 'block';
            document.getElementById('ttsPauseIcon').style.display = 'none';
        });
    }
});

function seekTTS(event) {
    const audio = document.getElementById('ttsPreviewAudio');
    const progressBar = document.getElementById('ttsProgressBar');

    const rect = progressBar.getBoundingClientRect();
    const percent = (event.clientX - rect.left) / rect.width;

    audio.currentTime = percent * audio.duration;
}

async function regenerateTTSPreview() {
    // 更新指令
    updateTTSPreviewInstruction();

    // 重新生成
    await generateTTSPreview();
}

function formatTime(seconds) {
    if (!seconds || seconds < 0) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Style Selection
function setStyle(style) {
    currentStyle = style;
    document.querySelectorAll('.style-btn').forEach(btn => btn.classList.remove('active'));
    // 找到对应风格的按钮（通过文本内容匹配）
    const btns = document.querySelectorAll('.style-btn');
    btns.forEach(btn => {
        if (btn.textContent.trim() === style) {
            btn.classList.add('active');
        }
    });
    document.getElementById('style').value = style;

    // 如果使用 MOSS-TTS，刷新音色推荐
    if (currentTTSProvider === 'moss') {
        loadVoiceRecommendation();
    }
}

// Error Display
function showError(message) {
    const el = document.getElementById('errorMessage');
    el.textContent = message;
    el.style.display = 'block';
}

function hideError() {
    document.getElementById('errorMessage').style.display = 'none';
}

// Format Size
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(1) + ' MB';
}

// ── 进度管理 ──

function updateProgress(percent, step, message) {
    // 更新进度条
    const progressFill = document.getElementById('progressFill');
    progressFill.style.width = `${percent}%`;
    progressFill.classList.add('animating');
    setTimeout(() => progressFill.classList.remove('animating'), 500);

    // 更新百分比
    document.getElementById('progressPercent').textContent = `${Math.round(percent)}%`;

    // 更新步骤状态 (1-8)
    document.querySelectorAll('.step-item').forEach((s, idx) => {
        const stepNum = idx + 1;
        if (stepNum < step) {
            s.classList.remove('active');
            s.classList.add('completed');
        } else if (stepNum === step) {
            s.classList.add('active');
            s.classList.remove('completed');
        } else {
            s.classList.remove('active', 'completed');
        }
    });

    // 添加日志
    if (message) {
        addLog(message);
    }
}

function addLog(message, type = 'info') {
    const log = document.getElementById('progressLog');
    const item = document.createElement('div');
    item.className = `log-item ${type}`;
    item.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    log.appendChild(item);
    log.scrollTop = log.scrollHeight;
}

function resetProgress() {
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressPercent').textContent = '0%';
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'completed'));
    document.getElementById('step1').classList.add('active');
    document.getElementById('progressLog').innerHTML = '';
}

// ── WebSocket 进度同步 ──

function connectWebSocket(sessionId) {
    // 检查浏览器是否支持 WebSocket
    if (!window.WebSocket) {
        console.log('WebSocket 不支持，使用轮询模式');
        startPolling(sessionId);
        return;
    }

    const wsUrl = `${API_BASE.replace('http', 'ws')}/ws/progress/${sessionId}`;

    try {
        wsConnection = new WebSocket(wsUrl);

        wsConnection.onopen = function() {
            addLog('WebSocket 连接成功', 'success');
        };

        wsConnection.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                handleProgressMessage(data);
            } catch (e) {
                console.error('解析消息失败:', e);
            }
        };

        wsConnection.onerror = function(error) {
            console.log('WebSocket 错误，切换到轮询模式');
            addLog('WebSocket 连接失败，使用轮询模式', 'warning');
            startPolling(sessionId);
        };

        wsConnection.onclose = function() {
            console.log('WebSocket 连接关闭');
        };

    } catch (e) {
        console.log('WebSocket 创建失败，使用轮询模式');
        startPolling(sessionId);
    }
}

// ── 步骤映射 ──
// 后台实际步骤: 1-音乐分析, 2-叙事生成, 3-素材选择, 4-转场映射, 5-字幕同步, 6-TTS合成, 7-素材下载, 8-视频渲染
const STEP_MAP = {
    1: { percent: 10, msg: '音乐情感分析' },
    2: { percent: 25, msg: 'AI 叙事生成' },
    3: { percent: 35, msg: '视觉素材选择' },
    4: { percent: 45, msg: '转场效果映射' },
    5: { percent: 55, msg: '字幕同步' },
    6: { percent: 68, msg: 'TTS 语音合成' },
    7: { percent: 80, msg: '视觉素材下载' },
    8: { percent: 95, msg: '视频渲染' },
};

function handleProgressMessage(data) {
    const step = data.step || 0;
    const percent = data.percent || (STEP_MAP[step]?.percent || 0);
    const status = data.status || '';
    const message = data.message || '';
    const sessionId = data.session_id || '';

    // 更新 outputId（从进度消息中获取）
    if (sessionId && sessionId.startsWith('sync-')) {
        outputId = sessionId;
    }

    // 直接使用后台进度
    updateProgress(percent, step, message);

    if (status === 'completed') {
        addLog('生产完成!', 'success');
        setTimeout(() => {
            showOutput({
                output_id: outputId,
                download_url: `${API_BASE}/api/download/${outputId}`
            });
        }, 1000);
    } else if (status === 'failed' || status === 'error') {
        addLog(`错误: ${message}`, 'error');
        showError(data.result?.error || message || '生产失败');
        resetProgressUI();
    }
}

// 轮询模式（WebSocket 不可用时）
function startPolling(sessionId) {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/status/${sessionId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                clearInterval(pollInterval);
                handleProgressMessage({
                    step: 6,
                    status: 'completed',
                    message: '视频生产完成',
                    download_url: data.download_url
                });
            }
        } catch (e) {
            console.error('轮询失败:', e);
        }
    }, 2000);
}

function resetProgressUI() {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('produceBtn').disabled = false;
    document.getElementById('produceBtn').textContent = '开始生产';
}

// ── 开始生产 ──

async function startProduction() {
    hideError();
    resetProgress();

    const theme = document.getElementById('theme').value.trim();
    const visualMode = document.getElementById('visualMode').value;

    // 流程检查：必须先上传音乐
    if (!uploadedFile) {
        showError('请先上传背景音乐');
        return;
    }

    // 流程检查：必须生成并确认文案
    if (!narrativeGenerated) {
        showError('请先点击"生成文案"并确认文案内容');
        return;
    }

    if (!confirmedNarrative) {
        showError('请确认文案后再开始生产');
        // 自动触发确认
        const narrative = getFinalNarrative();
        if (narrative.narration_script) {
            confirmedNarrative = narrative;
            addLog('自动确认文案', 'info');
        } else {
            return;
        }
    }

    // 流程检查：必须预览并确认TTS（如果有旁白）
    if (confirmedNarrative.narration_script && !ttsPreviewed) {
        showError('请先生成语音预览并确认语音参数');
        return;
    }

    if (confirmedNarrative.narration_script && !confirmedTTSParams) {
        showError('请确认语音参数后再开始生产');
        return;
    }

    // 显示进度区域
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('produceBtn').disabled = true;
    document.getElementById('produceBtn').textContent = '生产中...';
    document.getElementById('outputSection').style.display = 'none';

    addLog('开始生产...');
    updateProgress(5, 1, '准备生产参数...');

    try {
        // 构建请求体 - 使用确认的文案和TTS参数
        const requestBody = {
            theme: theme,
            bgm_path: uploadedFile.file_path,
            style: currentStyle,
            template: currentTemplate,
            ratio: currentRatio,
            visual_mode: visualMode,
            subtitle_style: currentSubtitleStyle,
            mode: currentMode,
            duration_limit: currentMode === 'short' ? currentDuration : null,
            transition_intensity: currentTransition,
            // 使用确认的文案
            title_text: confirmedNarrative.title_text,
            narration_script: confirmedNarrative.narration_script,
            // 使用确认的TTS参数
            tts_provider: confirmedTTSParams?.tts_provider || currentTTSProvider,
            voice: confirmedTTSParams?.voice || currentVoiceId,
            tts_instruction: confirmedTTSParams?.tts_instruction || document.getElementById('mossInstruction')?.value || '',
        };

        // 短视频模式自动增加分段数
        if (currentMode === 'short') {
            requestBody.segment_count = Math.round(currentDuration / 2);  // 30s → 15段
        }

        // 尝试使用异步生产（WebSocket 进度）
        try {
            // 生成临时 session_id 用于进度推送
            const tempSessionId = 'sync-' + Date.now();

            // 先连接 WebSocket
            connectWebSocket(tempSessionId);

            requestBody.session_id = tempSessionId;

            const asyncResponse = await fetch(`${API_BASE}/api/produce`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const asyncData = await asyncResponse.json();

            if (asyncData.success) {
                outputId = asyncData.output_id;
                // WebSocket 已连接，等待进度推送
                addLog('生产任务启动，等待进度...', 'success');
                return;
            } else {
                addLog('生产失败: ' + asyncData.error, 'error');
                showError(asyncData.error || '视频生产失败');
                resetProgressUI();
            }
        } catch (e) {
            addLog('WebSocket 模式失败，使用同步模式', 'warning');
            // 回退到同步模式（无实时进度）
            updateProgress(10, 1, '开始音乐分析...');

            const response = await fetch(`${API_BASE}/api/produce`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();

            if (data.success) {
                // 模拟进度动画（WebSocket 不可用时）
                const steps = [
                    { step: 1, percent: 15, msg: '音乐情感分析完成' },
                    { step: 2, percent: 25, msg: 'AI 叙事生成完成' },
                    { step: 3, percent: 35, msg: '视觉素材选择完成' },
                    { step: 4, percent: 45, msg: '转场效果映射完成' },
                    { step: 5, percent: 55, msg: '字幕同步完成' },
                    { step: 6, percent: 68, msg: 'TTS 语音合成完成' },
                    { step: 7, percent: 80, msg: '视觉素材下载完成' },
                    { step: 8, percent: 95, msg: '视频渲染完成' },
                ];

                for (const s of steps) {
                    await new Promise(resolve => setTimeout(resolve, 500));
                    updateProgress(s.percent, s.step, s.msg);
                }

                outputId = data.output_id;
                setTimeout(() => showOutput(data), 500);
            } else {
                addLog('生产失败: ' + data.error, 'error');
                showError(data.error || '视频生产失败');
                resetProgressUI();
            }
        }
    } catch (err) {
        addLog('请求失败: ' + err.message, 'error');
        showError('请求失败: ' + err.message);
        resetProgressUI();
    }
}

// Show Output
function showOutput(data) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('outputSection').style.display = 'block';

    const video = document.getElementById('outputVideo');
    const wrapper = document.getElementById('outputVideoWrapper');
    video.src = data.download_url || `${API_BASE}/api/download/${outputId}`;

    // 根据视频比例调整展示尺寸
    if (currentRatio === '9:16') {
        // 竖版视频：限制宽度，模拟手机屏幕
        wrapper.classList.add('ratio-vertical');
        wrapper.classList.remove('ratio-horizontal');
    } else {
        // 横版视频：正常展示
        wrapper.classList.add('ratio-horizontal');
        wrapper.classList.remove('ratio-vertical');
    }

    document.getElementById('outputInfo').textContent = `主题：${document.getElementById('theme').value} | 风格：${currentStyle} | TTS: ${currentTTSProvider} | 比例：${currentRatio}`;

    document.getElementById('produceBtn').disabled = false;
    document.getElementById('produceBtn').textContent = '重新生产';

    // 关闭 WebSocket
    if (wsConnection) {
        wsConnection.close();
        wsConnection = null;
    }
}

// Download Video
function downloadVideo() {
    if (outputId) {
        window.open(`${API_BASE}/api/download/${outputId}`, '_blank');
    }
}

// Initialize
document.getElementById('style').addEventListener('change', function() {
    setStyle(this.value);
});

// 初始化字幕预览
updateSubtitleDemo();

// 初始化 TTS 设置（默认 MOSS）
document.getElementById('mossSettings').style.display = 'flex';
loadVoiceRecommendation();

// ESC 关闭预览模态框
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closePreviewModal();
    }
});

// 点击模态框外部关闭
document.getElementById('previewModal').addEventListener('click', function(e) {
    if (e.target === this) {
        closePreviewModal();
    }
});

// ── 音色推荐功能 ──

// 加载音色推荐
async function loadVoiceRecommendation() {
    const theme = document.getElementById('theme').value;
    if (!theme) {
        // 使用默认推荐
        await loadDefaultVoiceRecommendation();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/voice/recommend`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                narrative: theme,
                style: currentStyle
            })
        });

        const data = await response.json();
        if (data.success) {
            voiceRecommendation = data.recommendation;
            displayVoiceRecommendation(voiceRecommendation);
            populateVoiceSelect(voiceRecommendation);
        }
    } catch (err) {
        console.error('音色推荐加载失败:', err);
        await loadDefaultVoiceRecommendation();
    }
}

// 加载默认音色库
async function loadDefaultVoiceRecommendation() {
    try {
        const response = await fetch(`${API_BASE}/api/voice/library`);
        const data = await response.json();
        if (data.success) {
            populateVoiceSelectFromLibrary(data.voices);
            // 默认推荐温暖女声
            selectVoiceFromLibrary('zh_female_chengnian');
        }
    } catch (err) {
        console.error('音色库加载失败:', err);
    }
}

// 显示推荐音色信息
function displayVoiceRecommendation(recommendation) {
    const voice = recommendation.recommended_voice;
    if (!voice) return;

    // 更新音色卡片
    document.getElementById('voiceName').textContent = voice.description;
    document.getElementById('voiceGenderTag').textContent = voice.gender === 'male' ? '男声' : '女声';
    document.getElementById('voiceAgeTag').textContent = getAgeLabel(voice.age);
    document.getElementById('voiceToneTag').textContent = getToneLabel(voice.tone);
    document.getElementById('voiceDesc').textContent = `适合${recommendation.detected_emotion || '治愈'}风格的视频`;

    // 更新头像颜色
    const avatar = document.getElementById('voiceAvatar');
    avatar.classList.remove('male', 'female');
    avatar.classList.add(voice.gender);

    // 更新指令预览
    document.getElementById('instructionPreview').textContent = voice.tts_instruction;
    document.getElementById('mossInstruction').value = voice.tts_instruction;

    currentVoiceId = voice.voice_id;

    // 显示检测信息
    console.log(`检测情感: ${recommendation.detected_emotion}, 内容类型: ${recommendation.detected_content_type}`);
}

// 填充音色选择下拉框
function populateVoiceSelect(recommendation) {
    const select = document.getElementById('voiceSelect');
    select.innerHTML = '<option value="">AI 推荐音色</option>';

    // 添加推荐音色
    if (recommendation.recommended_voice) {
        const opt = document.createElement('option');
        opt.value = recommendation.recommended_voice.voice_id;
        opt.textContent = `★ ${recommendation.recommended_voice.description}`;
        opt.selected = true;
        select.appendChild(opt);
    }

    // 添加备选音色
    recommendation.alternative_voices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.voice_id;
        opt.textContent = v.description;
        select.appendChild(opt);
    });
}

// 从音色库填充下拉框
function populateVoiceSelectFromLibrary(voices) {
    const select = document.getElementById('voiceSelect');
    select.innerHTML = '<option value="">选择音色</option>';

    voices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.voice_id;
        opt.textContent = v.description;
        if (v.voice_id === currentVoiceId) opt.selected = true;
        select.appendChild(opt);
    });
}

// 音色变更处理
async function onVoiceChange() {
    const voiceId = document.getElementById('voiceSelect').value;
    if (!voiceId) return;

    currentVoiceId = voiceId;
    await updateVoiceDisplay(voiceId);
    generateFinalInstruction();
}

// 更新音色显示
async function updateVoiceDisplay(voiceId) {
    try {
        const response = await fetch(`${API_BASE}/api/voice/library`);
        const data = await response.json();
        if (data.success) {
            const voice = data.voices.find(v => v.voice_id === voiceId);
            if (voice) {
                document.getElementById('voiceName').textContent = voice.description;
                document.getElementById('voiceGenderTag').textContent = voice.gender === 'male' ? '男声' : '女声';
                document.getElementById('voiceAgeTag').textContent = getAgeLabel(voice.age);
                document.getElementById('voiceToneTag').textContent = getToneLabel(voice.tone);

                const avatar = document.getElementById('voiceAvatar');
                avatar.classList.remove('male', 'female');
                avatar.classList.add(voice.gender);
            }
        }
    } catch (err) {
        console.error('获取音色信息失败:', err);
    }
}

// 刷新音色推荐
async function refreshVoiceRecommendation() {
    await loadVoiceRecommendation();
}

// ── MOSS-TTS 模板调整 ──

// 应用预设模板
async function applyPresetTemplate(presetKey) {
    // 更新按钮状态
    document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
    event.target.closest('.preset-btn').classList.add('active');

    // 预设映射
    const presetMap = {
        preset_energetic: { speed: 'speed_fast', pause: 'pause_short', emotion: 'emotion_energetic', voice: 'zh_male_qingnian' },
        preset_calm: { speed: 'speed_normal', pause: 'pause_normal', emotion: 'emotion_calm', voice: 'zh_female_chengnian' },
        preset_storytelling: { speed: 'speed_slow', pause: 'pause_long', emotion: 'emotion_warm', voice: 'zh_male_senior' },
        preset_news: { speed: 'speed_normal', pause: 'pause_short', emotion: 'emotion_serious', voice: 'zh_male_chengnian' },
        preset_podcast: { speed: 'speed_normal', pause: 'pause_normal', emotion: 'emotion_lively', voice: 'zh_female_shaonian' }
    };

    const preset = presetMap[presetKey];
    if (preset) {
        currentSpeedTemplate = preset.speed;
        currentPauseTemplate = preset.pause;
        currentEmotionTemplate = preset.emotion;
        currentVoiceId = preset.voice;

        // 更新模板按钮状态
        updateTemplateButtonStates();
        await updateVoiceDisplay(currentVoiceId);
        generateFinalInstruction();
    }
}

// 应用语速模板
function applySpeedTemplate(templateKey) {
    currentSpeedTemplate = templateKey;
    updateTemplateButtonStates();
    generateFinalInstruction();
}

// 应用停顿模板
function applyPauseTemplate(templateKey) {
    currentPauseTemplate = templateKey;
    updateTemplateButtonStates();
    generateFinalInstruction();
}

// 应用情感模板
function applyEmotionTemplate(templateKey) {
    currentEmotionTemplate = templateKey;
    updateTemplateButtonStates();
    generateFinalInstruction();
}

// 更新模板按钮状态
function updateTemplateButtonStates() {
    // 语速按钮
    document.querySelectorAll('.template-group').forEach(group => {
        const label = group.querySelector('label');
        if (label && label.textContent === '语速') {
            group.querySelectorAll('.template-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.onclick && btn.onclick.toString().includes(currentSpeedTemplate)) {
                    btn.classList.add('active');
                }
            });
        }
        if (label && label.textContent === '停顿') {
            group.querySelectorAll('.template-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.onclick && btn.onclick.toString().includes(currentPauseTemplate)) {
                    btn.classList.add('active');
                }
            });
        }
        if (label && label.textContent === '情感风格') {
            group.querySelectorAll('.template-btn').forEach(btn => {
                btn.classList.remove('active');
                if (btn.onclick && btn.onclick.toString().includes(currentEmotionTemplate)) {
                    btn.classList.add('active');
                }
            });
        }
    });
}

// 生成最终指令
async function generateFinalInstruction() {
    try {
        const response = await fetch(`${API_BASE}/api/voice/generate-instruction`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                voice_id: currentVoiceId,
                speed_template: currentSpeedTemplate,
                pause_template: currentPauseTemplate,
                emotion_template: currentEmotionTemplate
            })
        });

        const data = await response.json();
        if (data.success) {
            document.getElementById('instructionPreview').textContent = data.instruction;
            document.getElementById('mossInstruction').value = data.instruction;
        }
    } catch (err) {
        console.error('生成指令失败:', err);
        // 手动生成
        const parts = [];
        const voiceDesc = document.getElementById('voiceName').textContent;
        parts.push(voiceDesc);

        // 语速描述
        const speedDesc = {
            speed_fast: '语速较快',
            speed_normal: '语速适中',
            speed_slow: '语速缓慢'
        };
        parts.push(speedDesc[currentSpeedTemplate] || '语速适中');

        // 停顿描述
        const pauseDesc = {
            pause_short: '句间停顿较短',
            pause_normal: '句间停顿适中',
            pause_long: '句间停顿较长'
        };
        parts.push(pauseDesc[currentPauseTemplate] || '句间停顿适中');

        // 情感描述
        const emotionDesc = {
            emotion_energetic: '充满激情',
            emotion_calm: '平和舒缓',
            emotion_warm: '温暖治愈',
            emotion_serious: '沉稳有力',
            emotion_lively: '活泼俏皮'
        };
        parts.push(emotionDesc[currentEmotionTemplate] || '温暖治愈');

        const instruction = parts.join('，');
        document.getElementById('instructionPreview').textContent = instruction;
        document.getElementById('mossInstruction').value = instruction;
    }
}

// 从音色库选择音色
async function selectVoiceFromLibrary(voiceId) {
    currentVoiceId = voiceId;
    await updateVoiceDisplay(voiceId);
    document.getElementById('voiceSelect').value = voiceId;
    generateFinalInstruction();
}

// 年龄标签转换
function getAgeLabel(age) {
    const labels = {
        young: '青年',
        middle: '成年',
        senior: '老年'
    };
    return labels[age] || age;
}

// 语调标签转换
function getToneLabel(tone) {
    const labels = {
        energetic: '活力',
        calm: '平和',
        warm: '温暖',
        serious: '沉稳',
        lively: '活泼',
        firm: '坚定',
        kind: '慈祥',
        friendly: '友好'
    };
    return labels[tone] || tone;
}