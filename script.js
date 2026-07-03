let playlistData = null;
let artistsData = {};
let avatarData = {};

document.addEventListener('DOMContentLoaded', () => {
    loadPlaylist();
    setupEventListeners();
    setupScrollListener();
});

async function loadPlaylist() {
    try {
        const response = await fetch('data/playlist.json');
        playlistData = await response.json();
        processData();
        renderArtists();
        updateStats();
    } catch (error) {
        console.error('Failed to load playlist:', error);
        document.getElementById('empty-state').style.display = 'block';
        document.getElementById('empty-state').querySelector('.empty-text').textContent = '加载歌单失败，请检查网络连接';
    }
}

function processData() {
    artistsData = {};
    avatarData = playlistData.avatars || {};
    
    playlistData.groups.forEach(group => {
        group.songs.forEach(song => {
            if (!artistsData[song.artist]) {
                artistsData[song.artist] = {
                    songs: [],
                    groups: new Set(),
                    avatar: avatarData[song.artist] || null
                };
            }
            artistsData[song.artist].songs.push({
                    title: song.title
                });
            artistsData[song.artist].groups.add(group.name);
        });
    });
    
    Object.keys(artistsData).forEach(artist => {
        artistsData[artist].groups = Array.from(artistsData[artist].groups);
        artistsData[artist].songs.sort((a, b) => a.title.localeCompare(b.title, 'ja'));
    });
}

function updateStats() {
    const totalSongs = playlistData.total_songs;
    const totalArtists = Object.keys(artistsData).length;
    const updatedAt = new Date(playlistData.updated_at).toLocaleString('zh-CN');
    
    document.getElementById('total-songs').textContent = totalSongs;
    document.getElementById('total-artists').textContent = totalArtists;
    document.getElementById('last-updated').textContent = `更新于 ${updatedAt}`;
}

function renderArtists(filterGroup = 'all', searchQuery = '') {
    const container = document.getElementById('artists-container');
    container.innerHTML = '';
    
    let filteredArtists = Object.entries(artistsData);
    
    if (filterGroup !== 'all') {
        filteredArtists = filteredArtists.filter(([_, data]) => 
            data.groups.includes(filterGroup)
        );
    }
    
    if (searchQuery) {
        const query = searchQuery.toLowerCase();
        filteredArtists = filteredArtists.filter(([artist, data]) => {
            const artistMatch = artist.toLowerCase().includes(query);
            const songMatch = data.songs.some(song => 
                song.title.toLowerCase().includes(query)
            );
            return artistMatch || songMatch;
        });
    }
    
    filteredArtists.sort((a, b) => a[0].localeCompare(b[0]));
    
    if (filteredArtists.length === 0) {
        document.getElementById('empty-state').style.display = 'block';
        return;
    }
    
    document.getElementById('empty-state').style.display = 'none';
    
    filteredArtists.forEach(([artist, data], index) => {
        const card = document.createElement('div');
        card.className = 'artist-card expanded';
        card.style.animationDelay = `${index * 0.05}s`;
        
        const avatarImg = data.avatar 
            ? `<img src="${data.avatar}" alt="${artist}" class="artist-avatar" onerror="this.style.display='none'">`
            : '<span class="artist-avatar-placeholder">🎤</span>';
        
        const groupName = data.groups[0] ? data.groups[0].replace('系列', '') : '';
        
        card.innerHTML = `
            <div class="artist-header" onclick="toggleCard(this)">
                <div class="artist-info">
                    ${avatarImg}
                    <div>
                        <div class="artist-name">${artist}</div>
                        ${groupName ? `<div class="artist-meta">${groupName} · ${data.songs.length} 首歌曲</div>` : ''}
                    </div>
                </div>
                <div class="artist-header-right">
                    <span class="song-count">${data.songs.length}首</span>
                    <span class="toggle-icon">▼</span>
                </div>
            </div>
            <div class="songs-container" style="max-height: 1000px;">
                <div class="songs-list">
                    ${data.songs.map((song, songIndex) => `
                        <div class="song-item" data-title="${song.title}" onclick="copySongTitle(this)">
                            <span class="song-index">${songIndex + 1}</span>
                            <div class="song-info">
                                <div class="song-title">${song.title}</div>
                            </div>
                            <span class="copy-hint">点击复制</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function toggleCard(header) {
    const card = header.parentElement;
    const container = card.querySelector('.songs-container');
    
    card.classList.toggle('expanded');
    
    if (card.classList.contains('expanded')) {
        container.style.maxHeight = container.scrollHeight + 'px';
    } else {
        container.style.maxHeight = '0';
    }
}

function setupEventListeners() {
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const clearBtn = document.getElementById('clear-btn');
    const filterTabs = document.querySelectorAll('.filter-tab');
    const backToTop = document.createElement('div');
    
    backToTop.className = 'back-to-top';
    backToTop.innerHTML = '▲';
    backToTop.onclick = scrollToTop;
    document.body.appendChild(backToTop);
    
    searchBtn.addEventListener('click', () => {
        handleSearch(searchInput.value);
    });
    
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch(searchInput.value);
        }
    });
    
    searchInput.addEventListener('input', () => {
        handleSearch(searchInput.value);
    });
    
    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        const activeTab = document.querySelector('.filter-tab.active');
        renderArtists(activeTab.dataset.filter, '');
    });
    
    filterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            filterTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderArtists(tab.dataset.filter, searchInput.value);
        });
    });
}

function handleSearch(query) {
    const trimmedQuery = query.trim();
    
    if (trimmedQuery) {
        document.getElementById('clear-btn').style.display = 'block';
    } else {
        document.getElementById('clear-btn').style.display = 'none';
    }
    
    const activeTab = document.querySelector('.filter-tab.active');
    renderArtists(activeTab.dataset.filter, trimmedQuery);
}

function setupScrollListener() {
    const backToTop = document.querySelector('.back-to-top');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            backToTop.classList.add('show');
        } else {
            backToTop.classList.remove('show');
        }
    });
}

function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

function copySongTitle(element) {
    const title = element.dataset.title;
    
    navigator.clipboard.writeText(title).then(() => {
        element.classList.add('copied');
        const hint = element.querySelector('.copy-hint');
        if (hint) {
            hint.textContent = '已复制!';
        }
        
        setTimeout(() => {
            element.classList.remove('copied');
            if (hint) {
                hint.textContent = '点击复制';
            }
        }, 2000);
    }).catch(err => {
        console.error('复制失败:', err);
    });
}