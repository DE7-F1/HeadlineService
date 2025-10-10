// API 기본 URL 설정
const API_BASE_URL = (() => {
  // 개발환경: 127.0.0.1:8000 (백엔드 서버)
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://127.0.0.1:8000';
  }
  // 배포환경: 같은 IP의 8000번 포트 (백엔드 서버)
  return `http://${window.location.hostname}:8000`;
})();

async function fetchNews(keyword) {
  const titleEl = document.getElementById('results-title');
  const listEl  = document.getElementById('news-list-container');
  const panelEl = document.querySelector('.right-panel');

  if (!listEl) return;
  titleEl.hidden = false;
  listEl.hidden  = false;
  if (panelEl) panelEl.hidden = false;

  listEl.innerHTML = '<li>뉴스를 불러오는 중...</li>';

  try {
    const response = await fetch(`${API_BASE_URL}/news/headline/?keyword=${encodeURIComponent(keyword)}`);
    const data = await response.json();
    
    listEl.innerHTML = '';
    
    if (!data.success) {
      listEl.innerHTML = `<li>오류: ${data.message}</li>`;
      return;
    }
    
    if (data.data && data.data.length > 0) {
      data.data.forEach(news => {
        const li = document.createElement('li');
        li.innerHTML = `<a href="${news.url}" target="_blank">${news.title}</a>`;
        listEl.appendChild(li);
      });
    } else {
      listEl.innerHTML = '<li>관련 뉴스가 없습니다.</li>';
    }
  } catch (error) {
    console.error('뉴스 조회 오류:', error);
    listEl.innerHTML = '<li>뉴스를 불러오는 중 오류가 발생했습니다.</li>';
  }
}

async function drawWordCloud() {
  const wordCloudElement = document.getElementById('word-cloud-html');
  if (!wordCloudElement) return;

  wordCloudElement.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666; flex-direction: column;">
    <div class="spinner-border text-primary mb-3" role="status">
      <span class="sr-only">로딩중...</span>
    </div>
    <p>워드클라우드를 불러오는 중...</p>
  </div>`;

  try {
    const response = await fetch(`${API_BASE_URL}/news/wordcloud/`);
    const data = await response.json();
    
    if (!data.success) {
      wordCloudElement.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">
        <p>오류: ${data.message}</p>
      </div>`;
      return;
    }
    
    const words = data.data.map(item => [item.text, item.value]);

    WordCloud(wordCloudElement, {
      list: words,
      classes: 'word-cloud-item',
      gridSize: 10,
      color: 'random-dark',
      rotateRatio: 0,
      weightFactor: 10,
      shrinkToFit: true
    });

    setupWordCloudEvents();
    
    if (data.result_id) {
      console.log(`워드클라우드 결과 ID: ${data.result_id} (캐시됨)`);
    }
    
  } catch (error) {
    console.error('워드클라우드 로드 오류:', error);
    wordCloudElement.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666; flex-direction: column;">
      <i class="fas fa-exclamation-triangle fa-2x mb-3" style="color: #dc3545;"></i>
      <p>워드클라우드를 불러오는 중 오류가 발생했습니다.</p>
      <small class="text-muted">잠시 후 다시 시도해주세요.</small>
    </div>`;
  }
}


let currentFilters = {
  publisherIds: null,
  startDate: null,
  endDate: null,
  searchTerm: null
};

// 검색
document.addEventListener('DOMContentLoaded', async () => {

  await loadPublisherMapping();
  
  drawWordCloud();
  
  const searchForm = document.getElementById('search-form');
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const searchInput = document.getElementById('search-input');
      const searchTerm = searchInput.value.trim();
      
      if (searchTerm) {
        // 검색 시 필터 초기화
        currentFilters.publisherIds = null;
        currentFilters.startDate = null;
        currentFilters.endDate = null;
        currentFilters.searchTerm = searchTerm;
        
        // 검색 기능 실행
        searchNews(searchTerm);
        searchInput.value = '';
        
        // 카테고리 선택 상태 초기화
        document.querySelectorAll('.collapse-item').forEach(item => {
          item.classList.remove('active');
        });
      }
    });
  }

  setupCategoryFilters();
});


function setupCategoryFilters() {
  // 언론사별
  const pressItems = document.querySelectorAll('#collapsePress .collapse-item');
  pressItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const publisherId = item.getAttribute('data-publisher-id');
      const pressName = item.textContent.trim();
      currentFilters.publisherIds = [publisherId];
      currentFilters.startDate = null; 
      currentFilters.endDate = null; 
      filterWordCloud();
      updateActiveFilter('press', pressName);
    });
  });

  // 날짜별
  const dateItems = document.querySelectorAll('#collapseWeather .collapse-item');
  dateItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const dateRange = item.textContent.trim();
      const dateRangeObj = getDateRange(dateRange);
      currentFilters.startDate = dateRangeObj.start_date;
      currentFilters.endDate = dateRangeObj.end_date;
      currentFilters.publisherIds = null;
      filterWordCloud();
      updateActiveFilter('date', dateRange);
    });
  });
}

// 필터 시각화
function updateActiveFilter(type, value) {
  
  document.querySelectorAll('.collapse-item').forEach(item => {
    item.classList.remove('active');
  });
  
  const items = document.querySelectorAll('.collapse-item');
  items.forEach(item => {
    if (item.textContent.trim() === value) {
      item.classList.add('active');
    }
  });
}

// 필터링 
async function filterWordCloud() {
  const wordCloudElement = document.getElementById('word-cloud-html');
  if (!wordCloudElement) return;

  let filterDesc = '';
  if (currentFilters.publisherIds) {
    const publisherNames = currentFilters.publisherIds.map(id => getPublisherName(id));
    filterDesc = `${publisherNames.join(', ')} 언론사`;
  } else if (currentFilters.startDate && currentFilters.endDate) {
    filterDesc = `${currentFilters.startDate} ~ ${currentFilters.endDate} 뉴스`;
  } else if (currentFilters.searchTerm) {
    filterDesc = `"${currentFilters.searchTerm}" 검색 결과`;
  } else {
    filterDesc = '전체 뉴스';
  }

  wordCloudElement.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666; flex-direction: column;">
    <div class="spinner-border text-primary mb-3" role="status">
      <span class="sr-only">로딩중...</span>
    </div>
    <p>${filterDesc}를 불러오는 중...</p>
  </div>`;
  
  try {
    const params = new URLSearchParams();
    
    if (currentFilters.publisherIds) {
      params.append('publishers', currentFilters.publisherIds.join(','));
    }
    
    if (currentFilters.startDate) {
      params.append('start_date', currentFilters.startDate);
    }
    
    if (currentFilters.endDate) {
      params.append('end_date', currentFilters.endDate);
    }
    
    console.log('필터링 파라미터:', params.toString());
    
    const response = await fetch(`${API_BASE_URL}/news/wordcloud/?${params}`);
    const data = await response.json();
    
    if (!data.success) {
      wordCloudElement.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">
        <p>오류: ${data.message}</p>
      </div>`;
      return;
    }
    
    const words = data.data.map(item => [item.text, item.value]);
    
    // WordCloud 렌더링
    WordCloud(wordCloudElement, {
      list: words,
      classes: 'word-cloud-item',
      gridSize: 10,
      color: 'random-dark',
      rotateRatio: 0,
      weightFactor: 10,
      shrinkToFit: true
    });
    
    // 이벤트 리스너 재설정
    setupWordCloudEvents();
    
  } catch (error) {
    console.error('필터링 오류:', error);
    wordCloudElement.innerHTML = `<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #666;">
      <p>필터링 중 오류가 발생했습니다.</p>
    </div>`;
  }
}

// 검색 기능
async function searchNews(searchTerm) {
  const titleEl = document.getElementById('results-title');
  const listEl = document.getElementById('news-list-container');
  const panelEl = document.querySelector('.right-panel');

  if (!listEl) return;
  titleEl.hidden = false;
  listEl.hidden = false;
  if (panelEl) panelEl.hidden = false;

  listEl.innerHTML = '<li>검색 중...</li>';

  try {
    const response = await fetch(`${API_BASE_URL}/news/headline/?q=${encodeURIComponent(searchTerm)}`);
    const data = await response.json();
    
    listEl.innerHTML = '';
    
    if (!data.success) {
      listEl.innerHTML = `<li>오류: ${data.message}</li>`;
      return;
    }
    
    if (data.data && data.data.length > 0) {
      data.data.forEach(news => {
        const li = document.createElement('li');
        li.innerHTML = `<a href="${news.url}" target="_blank">${news.title}</a>`;
        listEl.appendChild(li);
      });
    } else {
      listEl.innerHTML = '<li>검색 결과가 없습니다.</li>';
    }
  } catch (error) {
    console.error('검색 오류:', error);
    listEl.innerHTML = '<li>검색 중 오류가 발생했습니다.</li>';
  }
}

// 실제 언론사 데이터를 API에서 가져와서 매핑
let publisherMapping = {};

async function loadPublisherMapping() {
  try {
    const response = await fetch(`${API_BASE_URL}/news/publisher/`);
    const data = await response.json();
    
    if (data && data.length > 0) {
      publisherMapping = {};
      data.forEach(publisher => {
        publisherMapping[publisher.id] = publisher.name;
      });
      console.log('언론사 매핑 로드 완료:', publisherMapping);
      

      updatePublisherCategories(data);
    }
  } catch (error) {
    console.error('언론사 데이터 로드 오류:', error);
    publisherMapping = {
      '1': 'KBS',
      '2': 'SBS', 
      '3': 'MBC',
      '4': 'JTBC',
      '5': 'YTN'
    };
  }
}


function updatePublisherCategories(publishers) {
  const pressContainer = document.querySelector('#collapsePress .collapse-inner');
  if (!pressContainer) return;
  
  pressContainer.innerHTML = '';
  
  // 실제 DB 데이터로 카테고리 생성
  publishers.forEach(publisher => {
    const link = document.createElement('a');
    link.className = 'collapse-item';
    link.href = 'javascript:void(0)';
    link.setAttribute('data-publisher-id', publisher.id);
    link.textContent = publisher.name;
    pressContainer.appendChild(link);
  });
  
  // 이벤트 리스너 재설정
  setupCategoryFilters();
}

function getPublisherName(publisherId) {
  return publisherMapping[publisherId] || 'Unknown';
}

function getDateRange(dateRange) {
  // 오늘 날짜 계산
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  const todayStr = `${year}-${month}-${day}`;
  
  if (dateRange === '오늘') {
    return {
      start_date: todayStr,
      end_date: todayStr
    };
  } else if (dateRange === '주간') {
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 6); 
    const weekAgoYear = weekAgo.getFullYear();
    const weekAgoMonth = String(weekAgo.getMonth() + 1).padStart(2, '0');
    const weekAgoDay = String(weekAgo.getDate()).padStart(2, '0');
    const weekAgoStr = `${weekAgoYear}-${weekAgoMonth}-${weekAgoDay}`;
    
    return {
      start_date: weekAgoStr,
      end_date: todayStr
    };
  }
  return {};
}

function setupWordCloudEvents() {
  const wordCloudElement = document.getElementById('word-cloud-html');
  if (!wordCloudElement) return;
  
  // 기존 이벤트 리스너 제거
  wordCloudElement.removeEventListener('wordcloudstop', handleWordCloudStop);
  wordCloudElement.removeEventListener('mousemove', handleMouseMove);
  
  // 새 이벤트 리스너 추가
  wordCloudElement.addEventListener('wordcloudstop', handleWordCloudStop);
  wordCloudElement.addEventListener('mousemove', handleMouseMove);
}

function handleWordCloudStop() {
  const wordCloudElement = document.getElementById('word-cloud-html');
  const spans = Array.from(document.querySelectorAll('#word-cloud-html .word-cloud-item'));
  
  wordCloudElement.classList.remove('entered');
  spans.forEach((span, idx) => {
    span.style.transition = 'opacity 420ms ease, transform 420ms ease';
    span.style.transitionDelay = `${Math.min(idx * 12, 240)}ms`;
    span.style.setProperty('--i', idx);
  });
  
  requestAnimationFrame(() => {
    wordCloudElement.classList.add('entered');
  });

  // 클릭 이벤트 설정
  document.querySelectorAll('#word-cloud-html .word-cloud-item')
    .forEach(span => {
      span.addEventListener('click', () => {
        const keyword = span.textContent;
        fetchNews(keyword);
      });
    });
}

function handleMouseMove(e) {
  const wordCloudElement = document.getElementById('word-cloud-html');
  const spans = Array.from(document.querySelectorAll('#word-cloud-html .word-cloud-item'));
  const rect = wordCloudElement.getBoundingClientRect();
  
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  const cx = rect.width / 2;
  const cy = rect.height / 2;
  const nx = (x - cx) / cx; // -1..1
  const ny = (y - cy) / cy; // -1..1
  
  if (window.raf) cancelAnimationFrame(window.raf);
  window.raf = requestAnimationFrame(() => {
    spans.forEach((s, i) => {
      const strength = 3; // px
      s.style.setProperty('--mx', `${nx * strength}px`);
      s.style.setProperty('--my', `${ny * strength}px`);
    });
  });
}

let resizeTimer; 

window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    
    resizeTimer = setTimeout(function() {
        drawWordCloud();
    }, 200);
});