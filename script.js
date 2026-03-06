let progressInterval;
let currentTabData = {};

// Tab switching logic
function switchTab(tabId) {
    // Update navigation buttons
    const navButtons = document.querySelectorAll('nav button');
    navButtons.forEach(btn => {
        btn.classList.remove('tab-active');
        btn.classList.add('text-gray-600', 'hover:bg-gray-100');
    });
    
    const activeBtn = document.getElementById(`nav-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.add('tab-active');
        activeBtn.classList.remove('text-gray-600', 'hover:bg-gray-100');
    }
    
    // Update content sections
    const sections = document.querySelectorAll('.tab-content');
    sections.forEach(sec => sec.classList.add('hidden'));
    
    const activeSection = document.getElementById(`${tabId}-container`);
    if (activeSection) {
        activeSection.classList.remove('hidden');
    }
}

// Fetch Video/Audio info
async function fetchInfo(tabId) {
    const input = document.getElementById(`${tabId}-url`);
    const url = input.value.trim();
    const infoDiv = document.getElementById(`${tabId}-info`);
    
    if (!url) {
        showNotification('Please paste a valid URL', 'error');
        return;
    }

    const platform = tabId.startsWith('youtube') ? 'youtube' : 'facebook';
    const type = tabId.endsWith('mp3') ? 'mp3' : 'mp4';
    
    // Show loading state on button
    const container = document.getElementById(`${tabId}-container`);
    const btn = container.querySelector('button');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Searching...';
    
    try {
        const response = await fetch(`/api/${platform}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url }),
            timeout: 30000 // 30 second timeout
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server response error:', response.status, errorText);
            throw new Error(`Server error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            showNotification(data.error, 'error');
        } else {
            currentTabData[tabId] = data;
            displayInfo(tabId, data, platform, type);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            showNotification('Network error. Please check your connection and try again.', 'error');
        } else if (error.message.includes('timeout')) {
            showNotification('Request timed out. Please try again.', 'error');
        } else {
            showNotification(`Error: ${error.message}`, 'error');
        }
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function displayInfo(tabId, data, platform, type) {
    const infoDiv = document.getElementById(`${tabId}-info`);
    infoDiv.classList.remove('hidden');
    
    let qualitiesHtml = '';
    if (type === 'mp4') {
        const formats = data.formats || [];
        if (platform === 'facebook') {
            // Filter out dash audio or other audio-only formats for the MP4 tab
            const videoFormats = formats.filter(f => !f.quality.toLowerCase().includes('audio'));
            
            // Special buttons for Facebook as requested: only show SD/HD if available
            const hasHD = videoFormats.some(f => f.quality.trim().toUpperCase() === 'HD');
            const hasSD = videoFormats.some(f => f.quality.trim().toUpperCase() === 'SD');
            
            // If neither HD nor SD specifically found, but video formats exist, show what's available
            if (!hasHD && !hasSD && videoFormats.length > 0) {
                qualitiesHtml = `
                    <div class="mb-6">
                        <label class="block text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Select Quality</label>
                        <div class="flex flex-col sm:flex-row gap-3">
                            ${videoFormats.map(f => `
                                <button onclick="downloadFile('${platform}', 'mp4', '${f.quality}', '${tabId}')" 
                                    class="px-6 py-3 bg-blue-600 text-white hover:bg-blue-700 rounded-xl transition-all font-bold text-base shadow-md flex items-center justify-center">
                                    <i class="fas fa-download mr-2"></i>Download Video ${f.quality}
                                </button>
                            `).join('')}
                        </div>
                    </div>`;
            } else {
                qualitiesHtml = `
                    <div class="mb-6">
                        <label class="block text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Select Quality</label>
                        <div class="flex flex-col sm:flex-row gap-3">
                            ${hasHD ? `
                                <button onclick="downloadFile('${platform}', 'mp4', 'HD', '${tabId}')" 
                                    class="px-6 py-3 bg-blue-600 text-white hover:bg-blue-700 rounded-xl transition-all font-bold text-base shadow-md flex items-center justify-center">
                                    <i class="fas fa-download mr-2"></i>Download Video HD
                                </button>` : ''}
                            ${hasSD ? `
                                <button onclick="downloadFile('${platform}', 'mp4', 'SD', '${tabId}')" 
                                    class="px-6 py-3 bg-gray-200 text-gray-800 hover:bg-gray-300 rounded-xl transition-all font-bold text-base shadow-md flex items-center justify-center">
                                    <i class="fas fa-download mr-2"></i>Download Video SD
                                </button>` : ''}
                        </div>
                    </div>`;
            }
        } else {
            // YouTube style
            qualitiesHtml = `
                <div class="mb-6">
                    <label class="block text-sm font-bold text-gray-700 mb-3 uppercase tracking-wider">Select Quality</label>
                    <div class="flex flex-wrap gap-3">
                        ${formats.map(f => `
                            <button onclick="downloadFile('${platform}', 'mp4', '${f.quality}', '${tabId}')" 
                                class="px-4 py-2 bg-gray-100 hover:bg-purple-600 hover:text-white rounded-lg transition-all font-bold text-sm border border-gray-200">
                                ${f.quality}
                            </button>
                        `).join('')}
                    </div>
                </div>`;
        }
    } else {
        qualitiesHtml = `
            <button onclick="downloadFile('${platform}', 'mp3', 'audio', '${tabId}')" 
                class="mt-4 w-full md:w-auto px-8 py-4 ${platform === 'youtube' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'} text-white rounded-xl font-bold transition-all shadow-lg flex items-center justify-center">
                <i class="fas fa-download mr-2"></i>Download MP3 Audio
            </button>`;
    }

    infoDiv.innerHTML = `
        <div class="md:flex">
            <div class="md:w-1/3 relative">
                <img src="${data.thumbnail}" alt="Thumbnail" class="w-full h-full object-cover">
                ${data.duration ? `<span class="absolute bottom-2 right-2 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded font-bold">${data.duration}</span>` : ''}
            </div>
            <div class="p-6 md:w-2/3">
                <h3 class="text-xl font-bold text-gray-800 mb-2 line-clamp-2">${data.title}</h3>
                ${data.description ? `<p class="text-gray-500 text-sm mb-4 line-clamp-2">${data.description}</p>` : ''}
                ${qualitiesHtml}
            </div>
        </div>
    `;
    
    infoDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function downloadFile(platform, type, quality, tabId) {
    const data = currentTabData[tabId];
    if (!data) return;

    const progressId = 'dl_' + Math.random().toString(36).substr(2, 9);
    showDownloadModal(data.title, quality === 'audio' ? 'MP3' : quality);
    startProgressPolling(progressId);

    try {
        const response = await fetch(`/api/download/${platform}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                videoId: data.videoId,
                quality: quality,
                title: data.title,
                progressId: progressId,
                type: type
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            const cleanTitle = data.title.replace(/[^\w\-_\. ]/g, '_');
            
            a.style.display = 'none';
            a.href = url;
            a.download = `${cleanTitle}_${quality}.${type}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            stopProgressPolling();
            showSuccessModal();
        } else {
            const err = await response.json();
            showNotification(err.error || 'Download failed', 'error');
            stopProgressPolling();
            closeModal();
        }
    } catch (error) {
        console.error('Download error:', error);
        showNotification('Download failed. Server might be busy.', 'error');
        stopProgressPolling();
        closeModal();
    }
}

// Progress Polling
function startProgressPolling(progressId) {
    stopProgressPolling();
    
    const progressBar = document.getElementById('modal-progress-bar');
    const speedText = document.getElementById('modal-speed');
    const sizeText = document.getElementById('modal-size');
    const percentText = document.getElementById('modal-percent');
    const statusText = document.getElementById('modal-status-text');
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/progress/${progressId}`);
            if (response.ok) {
                const data = await response.json();
                
                if (data.status === 'downloading') {
                    statusText.textContent = 'Downloading Media...';
                    const percent = data.numeric_percent || 0;
                    progressBar.style.width = `${percent}%`;
                    percentText.textContent = `${Math.round(percent)}%`;
                    speedText.textContent = data.speed_str || '0 B/s';
                    sizeText.textContent = `${data.downloaded_str} / ${data.total_str}`;
                    progressBar.querySelector('.animate-pulse')?.classList.remove('hidden');
                } else if (data.status === 'processing') {
                    statusText.textContent = 'Finalizing File...';
                    const percent = data.numeric_percent || 99;
                    progressBar.style.width = `${percent}%`;
                    percentText.textContent = `${Math.round(percent)}%`;
                    speedText.textContent = 'FFmpeg';
                    sizeText.textContent = data.msg || 'Processing...';
                    progressBar.querySelector('.animate-pulse')?.classList.remove('hidden');
                }
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }, 1000);
}

function stopProgressPolling() {
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

// Modal UI
function showDownloadModal(filename, quality) {
    const modal = document.getElementById('download-modal');
    const modalContent = document.getElementById('modal-content');
    const fileInfo = document.getElementById('modal-file-info');
    const loadingState = document.getElementById('modal-loading');
    const successState = document.getElementById('modal-success');
    const progressBar = document.getElementById('modal-progress-bar');
    const speedText = document.getElementById('modal-speed');
    const sizeText = document.getElementById('modal-size');
    const percentText = document.getElementById('modal-percent');
    const statusText = document.getElementById('modal-status-text');
    
    fileInfo.textContent = filename;
    statusText.textContent = 'Preparing Download...';
    progressBar.style.width = '0%';
    speedText.textContent = 'Initializing...';
    sizeText.textContent = '--- / ---';
    percentText.textContent = '0%';
    
    loadingState.classList.remove('hidden');
    successState.classList.add('hidden');
    modal.classList.remove('hidden');
    
    setTimeout(() => {
        modalContent.classList.remove('scale-95', 'opacity-0');
    }, 10);
}

function showSuccessModal() {
    const loadingState = document.getElementById('modal-loading');
    const successState = document.getElementById('modal-success');
    loadingState.classList.add('hidden');
    successState.classList.remove('hidden');
}

function closeModal() {
    const modal = document.getElementById('download-modal');
    const modalContent = document.getElementById('modal-content');
    modalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function showNotification(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-xl shadow-2xl z-50 transform transition-all duration-300 translate-y-20 opacity-0 font-bold ${
        type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
    }`;
    toast.innerHTML = `<i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2"></i>${message}`;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.remove('translate-y-20', 'opacity-0');
    }, 100);
    
    setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
