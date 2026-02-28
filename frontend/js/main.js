/**
 * Main Application Utilities
 * Common functions for UI, alerts, form handling, etc.
 */

// ========== Alert System ==========

function showAlert(message, type = 'info') {
    const alertBox = document.createElement('div');
    alertBox.className = `alert alert-${type}`;
    alertBox.innerHTML = `
        <span>${message}</span>
        <span class="alert-close">&times;</span>
    `;

    // Add to page
    const container = document.querySelector('main') || document.body;
    container.insertBefore(alertBox, container.firstChild);

    // Close button
    alertBox.querySelector('.alert-close').addEventListener('click', () => {
        alertBox.remove();
    });

    // Auto-dismiss after 5 seconds (except errors)
    if (type !== 'error' && type !== 'danger') {
        setTimeout(() => {
            alertBox.remove();
        }, 5000);
    }
}

function showSuccess(message) {
    showAlert(message, 'success');
}

function showError(message) {
    showAlert(message, 'error');
}

function showWarning(message) {
    showAlert(message, 'warning');
}

function showInfo(message) {
    showAlert(message, 'info');
}

// ========== Loading States ==========

function setLoading(element, isLoading = true) {
    if (!element) return;

    if (isLoading) {
        element.disabled = true;
        element.classList.add('loading');
        element.dataset.originalText = element.textContent;
        element.textContent = '⌛ Loading...';
    } else {
        element.disabled = false;
        element.classList.remove('loading');
        element.textContent = element.dataset.originalText || element.textContent;
    }
}

function showLoader(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = '<div class="loader"></div>';
    }
}

// ========== Form Utilities ==========

function getFormData(formElement) {
    const formData = new FormData(formElement);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    return data;
}

function setFormData(formElement, data) {
    Object.entries(data).forEach(([key, value]) => {
        const field = formElement.elements[key];
        if (field) {
            if (field.type === 'checkbox') {
                field.checked = value;
            } else if (field.type === 'radio') {
                document.querySelector(`input[name="${key}"][value="${value}"]`).checked = true;
            } else {
                field.value = value;
            }
        }
    });
}

function clearForm(formElement) {
    formElement.reset();
    formElement.querySelectorAll('.form-error').forEach(el => el.remove());
}

function showFormError(formElement, field, message) {
    const fieldElement = formElement.elements[field];
    if (!fieldElement) return;

    // Remove existing error
    const existingError = fieldElement.parentElement.querySelector('.form-error');
    if (existingError) {
        existingError.remove();
    }

    // Add new error
    const errorElement = document.createElement('div');
    errorElement.className = 'form-error';
    errorElement.textContent = message;
    fieldElement.parentElement.appendChild(errorElement);
    fieldElement.focus();
}

function clearFormErrors(formElement) {
    formElement.querySelectorAll('.form-error').forEach(el => el.remove());
}

// ========== Formatting Utilities ==========

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return formatDate(dateString);
}

// ========== Match Display Utilities ==========

function getMatchStrengthLabel(score) {
    if (score >= 90) return 'Perfect Match';
    if (score >= 80) return 'Excellent Match';
    if (score >= 70) return 'Very Good Match';
    if (score >= 60) return 'Good Match';
    if (score >= 50) return 'Okay Match';
    return 'Possible Match';
}

function getMatchStrengthClass(score) {
    if (score >= 90) return 'excellent';
    if (score >= 80) return 'excellent';
    if (score >= 70) return 'very-good';
    if (score >= 60) return 'good';
    return 'okay';
}

function renderMatchCard(match, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const strengthLabel = getMatchStrengthLabel(match.score);
    const strengthClass = getMatchStrengthClass(match.score);

    const initials = (match.user_name || '?').split(' ').map(n => n[0]).join('').toUpperCase();

    const explanation = match.explanation || {};
    const summary = explanation.summary || 'Great match!';
    const details = explanation.details || [];

    const html = `
        <div class="card match-card">
            <div class="match-avatar">${initials}</div>
            <div class="match-info">
                <div class="match-header">
                    <div>
                        <div class="match-name">${match.user_name}</div>
                        <div class="match-location">📍 ${match.city || 'Location unknown'}</div>
                    </div>
                    <div class="match-score">
                        <span class="score-badge">${match.score}%</span>
                    </div>
                </div>
                <div class="match-strength ${strengthClass}">${strengthLabel}</div>
                <div class="match-explanation">
                    ${summary}
                    ${details.length > 0 ? '<ul>' + details.map(d => `<li>${d}</li>`).join('') + '</ul>' : ''}
                </div>
                <div class="match-actions">
                    <button class="btn btn-primary btn-sm" onclick="handleLikeMatch(${match.user_id})">👍 Like</button>
                    <button class="btn btn-secondary btn-sm" onclick="handleDislikeMatch(${match.user_id})">👎 Dislike</button>
                </div>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', html);
}

function renderRoomCard(room, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const amenities = room.amenities ? room.amenities.split(',').map(a => a.trim()).slice(0, 3) : [];
    const amenitiesHtml = amenities.length > 0 
        ? '<div class="room-amenities">' + amenities.map(a => `<span class="badge">${a}</span>`).join('') + '</div>'
        : '';

    const html = `
        <div class="card room-card">
            <div class="card-header">
                <div>
                    <h3 class="card-title">${room.title}</h3>
                    <p class="text-light" style="margin: 0.25rem 0 0 0;">📍 ${room.location}</p>
                </div>
                <div class="text-right">
                    <div class="stat-value" style="margin: 0;">${formatCurrency(room.rent_price)}</div>
                    <div class="stat-label" style="margin: 0;">/month</div>
                </div>
            </div>
            <div class="card-body">
                <div class="room-details">
                    <span>🛏️ ${room.bed_size || 'Single'}</span>
                    <span>${room.furnishing || 'Unfurnished'}</span>
                    <span>${room.room_type || 'Room'}</span>
                </div>
                ${room.pets_allowed ? '<span class="badge badge-success">🐾 Pets OK</span>' : ''}
                ${room.smoking_allowed ? '<span class="badge badge-warning">🚬 Smoking OK</span>' : ''}
                ${amenitiesHtml}
                <p class="text-light mt-2">${room.description || 'No description provided'}</p>
            </div>
            <div class="card-footer">
                <button class="btn btn-primary" onclick="viewRoom(${room.room_id})">View Details</button>
                <button class="btn btn-secondary" onclick="contactOwner(${room.room_id})">Contact Owner</button>
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', html);
}

// ========== Modal Utilities ==========

function showModal(title, content, options = {}) {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-overlay" onclick="if(event.target === this) this.parentElement.remove()"></div>
        <div class="modal-content">
            <button type="button" class="modal-close" onclick="this.closest('.modal').remove()">×</button>
            <h2>${title}</h2>
            <div class="modal-body">${content}</div>
            ${options.footer ? `<div class="modal-footer">${options.footer}</div>` : ''}
        </div>
    `;
    
    document.body.appendChild(modal);
    return modal;
}

function closeModal(modal) {
    if (modal) {
        modal.remove();
    }
}

// ========== Confirmation Dialog ==========

function confirm(message) {
    return new Promise((resolve) => {
        const modal = showModal('Confirm', `<p>${message}</p>`, {
            footer: `
                <button class="btn btn-danger">Cancel</button>
                <button class="btn btn-primary">Confirm</button>
            `
        });

        const buttons = modal.querySelectorAll('.modal-footer button');
        buttons[0].onclick = () => {
            modal.remove();
            resolve(false);
        };
        buttons[1].onclick = () => {
            modal.remove();
            resolve(true);
        };
    });
}

// ========== Pagination Utilities ==========

function renderPagination(currentPage, totalPages, onPageChange) {
    const container = document.getElementById('pagination');
    if (!container) return;

    let html = '<div class="pagination">';

    // Previous button
    if (currentPage > 1) {
        html += `<a href="#" onclick="event.preventDefault(); arguments[1](${currentPage - 1})">← Previous</a>`;
    } else {
        html += '<span class="disabled">← Previous</span>';
    }

    // Page numbers
    for (let i = Math.max(1, currentPage - 2); i <= Math.min(totalPages, currentPage + 2); i++) {
        if (i === currentPage) {
            html += `<span class="active">${i}</span>`;
        } else {
            html += `<a href="#" onclick="event.preventDefault(); arguments[1](${i})">${i}</a>`;
        }
    }

    // Next button
    if (currentPage < totalPages) {
        html += `<a href="#" onclick="event.preventDefault(); arguments[1](${currentPage + 1})">Next →</a>`;
    } else {
        html += '<span class="disabled">Next →</span>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Re-attach click handlers
    container.querySelectorAll('a').forEach(link => {
        link.onclick = (e) => {
            e.preventDefault();
            const page = parseInt(link.textContent.match(/\d+/)[0]);
            onPageChange(page);
        };
    });
}

// ========== Navigation Utilities ==========

function setActiveNav(linkId) {
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.getElementById(linkId);
    if (activeLink) {
        activeLink.classList.add('active');
    }
}

// ========== Common Event Handlers ==========

async function handleLogout() {
    if (await confirm('Are you sure you want to logout?')) {
        await auth.logout();
    }
}

async function handleLikeMatch(userId) {
    try {
        // TODO: Implement like functionality
        showSuccess('Match liked! ❤️');
    } catch (error) {
        showError(error.message);
    }
}

async function handleDislikeMatch(userId) {
    try {
        // TODO: Implement dislike functionality
        showSuccess('Match disliked');
    } catch (error) {
        showError(error.message);
    }
}

function viewRoom(roomId) {
    window.location.href = `/room-detail.html?id=${roomId}`;
}

function contactOwner(roomId) {
    showInfo('Owner contact functionality coming soon!');
}

// ========== Initialization ==========

document.addEventListener('DOMContentLoaded', () => {
    // Setup logout buttons
    document.querySelectorAll('.logout-btn').forEach(btn => {
        btn.addEventListener('click', handleLogout);
    });

    // Require authentication on protected pages
    const protectedPages = ['dashboard.html', 'preferences.html', 'matches.html', 'rooms.html', 'profile.html'];
    const currentPage = window.location.pathname.split('/').pop();
    
    if (protectedPages.includes(currentPage) && !auth.isAuthenticated()) {
        window.location.href = '/login.html';
    }
});
