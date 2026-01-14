document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const removeBtn = document.getElementById('remove-file');
    const filePreview = document.getElementById('file-preview');
    const fileNameSpan = document.querySelector('.file-name');
    const fileSizeSpan = document.querySelector('.file-size');
    const loader = document.getElementById('loader');
    const resultsContainer = document.getElementById('results');

    let selectedFile = null;

    // Trigger file input click
    uploadArea.addEventListener('click', (e) => {
        if (e.target !== removeBtn && !removeBtn.contains(e.target)) {
            fileInput.click();
        }
    });

    // Handle File Selection
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag & Drop Events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    uploadArea.addEventListener('dragover', () => uploadArea.classList.add('drag-active'));
    uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-active'));

    uploadArea.addEventListener('drop', (e) => {
        uploadArea.classList.remove('drag-active');
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    function handleFile(file) {
        selectedFile = file;
        fileNameSpan.textContent = file.name;
        fileSizeSpan.textContent = formatBytes(file.size);

        uploadArea.classList.add('has-file');
        analyzeBtn.disabled = false;

        // Hide previous results
        resultsContainer.style.display = 'none';

        // Reset results animations if needed
    }

    removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedFile = null;
        fileInput.value = '';
        uploadArea.classList.remove('has-file');
        analyzeBtn.disabled = true;
        resultsContainer.style.display = 'none';
    });

    // Analyze Button Click
    analyzeBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        // UI State: Loading
        analyzeBtn.disabled = true;
        loader.style.display = 'flex';
        resultsContainer.style.display = 'none';

        // Prepare Form Data
        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Analysis failed');
            }

            const data = await response.json();
            displayResults(data);

        } catch (error) {
            console.error('Error:', error);
            alert(`Analysis Failed: ${error.message}`);
        } finally {
            // UI State: Reset
            loader.style.display = 'none';
            analyzeBtn.disabled = false;
        }
    });

    function displayResults(data) {
        const errorState = document.getElementById('error-state');
        const cvContent = document.getElementById('cv-content');

        // Handle Rejection
        if (!data.is_cv) {
            errorState.style.display = 'block';
            cvContent.style.display = 'none';
            document.getElementById('rejection-reason').textContent = data.rejection_reason || 'Document does not format as a CV.';

            resultsContainer.style.display = 'block';
            resultsContainer.scrollIntoView({ behavior: 'smooth' });
            return;
        }

        // Handle Valid CV
        errorState.style.display = 'none';
        cvContent.style.display = 'grid';

        const cv = data.cv_data;

        // Profile
        document.getElementById('cv-name').textContent = `${cv.first_name} ${cv.last_name}`;
        document.getElementById('cv-email').textContent = cv.email || 'N/A';
        document.getElementById('cv-phone').textContent = cv.phone || 'N/A';
        document.getElementById('cv-summary').textContent = cv.summary || 'No summary provided.';

        // Skills
        const skillsContainer = document.getElementById('cv-skills');
        skillsContainer.innerHTML = '';
        if (cv.skills && cv.skills.length > 0) {
            cv.skills.forEach(skill => {
                const span = document.createElement('span');
                span.className = 'tag';
                span.textContent = skill;
                skillsContainer.appendChild(span);
            });
        } else {
            skillsContainer.textContent = 'No skills listed.';
        }

        // Work Experience
        const experienceContainer = document.getElementById('cv-experience');
        experienceContainer.innerHTML = '';
        if (cv.work_experience && cv.work_experience.length > 0) {
            cv.work_experience.forEach(exp => {
                const li = document.createElement('li');
                li.className = 'timeline-item';
                li.innerHTML = `
                    <div class="timeline-marker"></div>
                    <div class="timeline-content">
                        <h4>${exp.role}</h4>
                        <span class="timeline-date">${exp.dates}</span>
                        <h5 class="timeline-company">${exp.company}</h5>
                        <p>${exp.description}</p>
                    </div>
                `;
                experienceContainer.appendChild(li);
            });
        } else {
            experienceContainer.innerHTML = '<p class="text-muted">No work experience listed.</p>';
        }

        // Education
        const educationContainer = document.getElementById('cv-education');
        educationContainer.innerHTML = '';
        if (cv.education && cv.education.length > 0) {
            cv.education.forEach(edu => {
                const li = document.createElement('li');
                li.className = 'timeline-item';
                li.innerHTML = `
                    <div class="timeline-marker"></div>
                    <div class="timeline-content">
                        <h4>${edu.degree}</h4>
                        <span class="timeline-date">${edu.dates}</span>
                        <h5 class="timeline-school">${edu.school}</h5>
                    </div>
                `;
                educationContainer.appendChild(li);
            });
        } else {
            educationContainer.innerHTML = '<p class="text-muted">No education listed.</p>';
        }

        // Show Results
        resultsContainer.style.display = 'block';
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }

    // Tabs Logic
    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.tab;

            // Update Tabs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update Content
            tabContents.forEach(c => c.classList.remove('active'));
            document.getElementById(`${target}-tab-content`).classList.add('active');

            if (target === 'warehouse') {
                loadWarehouseData();
            }
        });
    });

    // Warehouse Logic
    const warehouseSearch = document.getElementById('warehouse-search');
    const refreshWarehouseBtn = document.getElementById('refresh-warehouse');
    const cvList = document.getElementById('cv-list');

    let searchDebounce;
    warehouseSearch.addEventListener('input', (e) => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
            loadWarehouseData(e.target.value);
        }, 500);
    });

    refreshWarehouseBtn.addEventListener('click', () => {
        loadWarehouseData(warehouseSearch.value);
    });

    // Smart Search Logic
    const smartSearchInput = document.getElementById('smart-search-input');
    const smartSearchBtn = document.getElementById('smart-search-btn');

    smartSearchBtn.addEventListener('click', async () => {
        const query = smartSearchInput.value.trim();
        if (!query) return;

        smartSearchBtn.disabled = true;
        smartSearchBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Thinking...';
        cvList.innerHTML = '<div class="empty-state"><div class="scanner" style="width: 200px; margin: 0 auto 1rem;"></div><p>Asking Gemini to find the best candidates...</p></div>';

        try {
            const response = await fetch('/search/smart', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: query })
            });

            if (!response.ok) throw new Error('Search failed');

            const data = await response.json();
            renderSmartSearchResults(data.results);

        } catch (error) {
            console.error('Smart Search Error:', error);
            cvList.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Error performing smart search. Please try again.</p>
                </div>
            `;
        } finally {
            smartSearchBtn.disabled = false;
            smartSearchBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Ask AI';
        }
    });

    function renderSmartSearchResults(results) {
        if (!results || results.length === 0) {
            cvList.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-robot"></i>
                    <p>I couldn't find any candidates matching your description.</p>
                </div>
            `;
            return;
        }

        cvList.innerHTML = '';
        results.forEach(item => {
            const cv = item.cv;
            const matchReason = item.match_reason;
            const score = item.match_score;

            const div = document.createElement('div');
            div.className = 'cv-item';
            div.style.borderLeft = `4px solid ${getScoreColor(score)}`;

            const fullName = `${cv.first_name || 'Unknown'} ${cv.last_name || ''}`.trim();

            div.innerHTML = `
                <div class="cv-item-info">
                    <h4>
                        <i class="fa-solid fa-user-circle"></i> ${fullName}
                        <span class="cv-filename">${item.filename}</span>
                    </h4>
                    <p style="margin-top: 0.5rem; color: var(--text);"><strong><i class="fa-solid fa-check-double"></i> Match Reason:</strong> ${matchReason}</p>
                    <span class="match-badge" style="background: ${getScoreColor(score)}">${score}% Match</span>
                </div>
                <div class="cv-actions">
                     <i class="fa-solid fa-chevron-right arrow-icon"></i>
                </div>
            `;

            div.addEventListener('click', () => {
                viewCV(item.id);
            });

            cvList.appendChild(div);
        });
    }

    function getScoreColor(score) {
        if (score >= 90) return '#10b981'; // Green
        if (score >= 70) return '#f59e0b'; // Orange
        return '#ef4444'; // Red
    }

    async function loadWarehouseData(query = '') {
        cvList.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading CVs...</p></div>';

        try {
            let url = '/cvs';
            if (query) {
                url += `?q=${encodeURIComponent(query)}`;
            }

            const response = await fetch(url);
            if (!response.ok) throw new Error('Failed to fetch CVs');

            const cvs = await response.json();
            renderCVList(cvs);

        } catch (error) {
            console.error('Warehouse Error:', error);
            cvList.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>Error loading warehouse data. Please try again.</p>
                </div>
            `;
        }
    }

    function renderCVList(cvs) {
        if (!cvs || cvs.length === 0) {
            cvList.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-box-open"></i>
                    <p>No CVs found in the warehouse.</p>
                </div>
            `;
            return;
        }

        cvList.innerHTML = '';
        cvs.forEach(cv => {
            const item = document.createElement('div');
            item.className = 'cv-item';

            const fullName = `${cv.first_name || 'Unknown'} ${cv.last_name || ''}`.trim();
            const summary = cv.summary ? (cv.summary.length > 100 ? cv.summary.substring(0, 100) + '...' : cv.summary) : 'No summary available.';

            item.innerHTML = `
                <div class="cv-item-info">
                    <h4>
                        <i class="fa-solid fa-user-circle"></i> ${fullName}
                        <span class="cv-filename">${cv.filename || 'Unknown File'}</span>
                    </h4>
                    <p>${summary}</p>
                </div>
                <div class="cv-actions">
                     <button class="icon-btn-sm delete-btn" title="Delete CV">
                        <i class="fa-solid fa-trash"></i>
                     </button>
                     <i class="fa-solid fa-chevron-right arrow-icon"></i>
                </div>
            `;

            // View Details
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.delete-btn')) {
                    viewCV(cv.id);
                }
            });

            // Delete Action
            const deleteBtn = item.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (confirm(`Are you sure you want to delete ${fullName}?`)) {
                    deleteCV(cv.id);
                }
            });

            cvList.appendChild(item);
        });
    }

    async function viewCV(id) {
        cvList.innerHTML = '<div class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i><p>Loading details...</p></div>';

        try {
            const response = await fetch(`/cvs/${id}`);
            if (!response.ok) throw new Error('Failed to load CV details');

            const cvData = await response.json();
            renderDetailView(cvData);

        } catch (error) {
            console.error(error);
            loadWarehouseData();
            alert("Could not load CV details.");
        }
    }

    function renderDetailView(cv) {
        // Simple back button + content
        const detailHtml = `
            <div class="detail-toolbar">
                <button class="back-btn" id="back-to-list"><i class="fa-solid fa-arrow-left"></i> Back to List</button>
            </div>
            <div class="cv-grid-layout">
                 <div class="card profile-card">
                    <div class="card-header">
                        <i class="fa-solid fa-user"></i>
                        <h3>Candidate Profile</h3>
                    </div>
                    <div class="profile-details">
                        <h2>${cv.first_name} ${cv.last_name}</h2>
                        <div class="contact-info">
                            <p><i class="fa-solid fa-envelope"></i> ${cv.email || 'N/A'}</p>
                            <p><i class="fa-solid fa-phone"></i> ${cv.phone || 'N/A'}</p>
                        </div>
                        <div class="summary-section">
                            <h4>Professional Summary</h4>
                            <p>${cv.summary || 'No summary.'}</p>
                        </div>
                    </div>
                </div>

                <div class="card skills-card">
                    <div class="card-header">
                        <i class="fa-solid fa-microchip"></i>
                        <h3>Skills</h3>
                    </div>
                     <div class="card-body">
                        <div class="tags-container">
                            ${(cv.skills || []).map(s => `<span class="tag">${s}</span>`).join('')}
                        </div>
                    </div>
                </div>

                <div class="card experience-card">
                     <div class="card-header">
                        <i class="fa-solid fa-briefcase"></i>
                        <h3>Work Experience</h3>
                    </div>
                    <ul class="timeline">
                        ${(cv.work_experience || []).map(exp => `
                             <li class="timeline-item">
                                <div class="timeline-marker"></div>
                                <div class="timeline-content">
                                    <h4>${exp.role || 'Role'}</h4>
                                    <span class="timeline-date">${exp.dates || ''}</span>
                                    <h5 class="timeline-company">${exp.company || ''}</h5>
                                    <p>${exp.description || ''}</p>
                                </div>
                            </li>
                        `).join('')}
                    </ul>
                </div>
                 
                 <div class="card education-card">
                     <div class="card-header">
                        <i class="fa-solid fa-graduation-cap"></i>
                        <h3>Education</h3>
                    </div>
                    <ul class="timeline">
                         ${(cv.education || []).map(edu => `
                             <li class="timeline-item">
                                <div class="timeline-marker"></div>
                                <div class="timeline-content">
                                    <h4>${edu.degree || 'Degree'}</h4>
                                    <span class="timeline-date">${edu.dates || ''}</span>
                                    <h5 class="timeline-school">${edu.school || ''}</h5>
                                </div>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            </div>
        `;

        cvList.innerHTML = detailHtml;
        document.getElementById('back-to-list').addEventListener('click', () => {
            const searchVal = document.getElementById('warehouse-search').value;
            loadWarehouseData(searchVal);
        });
    }

    async function deleteCV(id) {
        try {
            const response = await fetch(`/cvs/${id}`, { method: 'DELETE' });
            if (response.ok) {
                const searchVal = document.getElementById('warehouse-search').value;
                loadWarehouseData(searchVal);
            } else {
                alert("Failed to delete CV");
            }
        } catch (e) {
            console.error(e);
            alert("Error deleting CV");
        }
    }

    function formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
});
