/**
 * Enhanced searchable select component for Remote Home Assistant
 * Provides real-time search, checkbox selection, and bulk operations
 */

class SearchableSelect extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._items = [];
    this._selected = new Set();
    this._searchTerm = '';
    this._isOpen = false;
  }

  connectedCallback() {
    this.render();
    this.setupEventListeners();
  }

  set items(value) {
    this._items = value || [];
    this.render();
  }

  set selected(value) {
    this._selected = new Set(value || []);
    this.render();
  }

  get selected() {
    return Array.from(this._selected);
  }

  setupEventListeners() {
    const searchInput = this.shadowRoot.querySelector('#search-input');
    const dropdown = this.shadowRoot.querySelector('.dropdown');
    
    // Search functionality
    searchInput.addEventListener('input', (e) => {
      this._searchTerm = e.target.value.toLowerCase();
      this.renderItems();
    });

    // Toggle dropdown
    searchInput.addEventListener('focus', () => {
      this._isOpen = true;
      dropdown.classList.add('open');
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!this.contains(e.target)) {
        this._isOpen = false;
        dropdown.classList.remove('open');
      }
    });

    // Select all/none buttons
    this.shadowRoot.querySelector('#select-all').addEventListener('click', () => {
      this.selectAll();
    });

    this.shadowRoot.querySelector('#select-none').addEventListener('click', () => {
      this.selectNone();
    });
  }

  selectAll() {
    const visibleItems = this.getFilteredItems();
    visibleItems.forEach(item => {
      if (!item.disabled) {
        this._selected.add(item.value);
      }
    });
    this.render();
    this.dispatchChangeEvent();
  }

  selectNone() {
    this._selected.clear();
    this.render();
    this.dispatchChangeEvent();
  }

  toggleItem(value) {
    if (this._selected.has(value)) {
      this._selected.delete(value);
    } else {
      this._selected.add(value);
    }
    this.render();
    this.dispatchChangeEvent();
  }

  dispatchChangeEvent() {
    this.dispatchEvent(new CustomEvent('change', {
      detail: { selected: this.selected },
      bubbles: true
    }));
  }

  getFilteredItems() {
    if (!this._searchTerm) {
      return this._items;
    }

    return this._items.filter(item => {
      if (item.disabled) return true; // Always show headers
      
      // Search in multiple fields
      const searchFields = [
        item.label?.toLowerCase(),
        item.value?.toLowerCase(),
        ...(item.search_terms || [])
      ].filter(Boolean);

      return searchFields.some(field => 
        field.includes(this._searchTerm)
      );
    });
  }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          position: relative;
          font-family: var(--paper-font-body1_-_font-family);
        }

        .search-container {
          position: relative;
          margin-bottom: 8px;
        }

        #search-input {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          font-size: 16px;
          box-sizing: border-box;
          background: var(--card-background-color);
          color: var(--primary-text-color);
        }

        #search-input:focus {
          outline: none;
          border-color: var(--primary-color);
        }

        .dropdown {
          display: none;
          position: absolute;
          top: 100%;
          left: 0;
          right: 0;
          max-height: 400px;
          overflow-y: auto;
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          z-index: 1000;
        }

        .dropdown.open {
          display: block;
        }

        .controls {
          display: flex;
          justify-content: space-between;
          padding: 8px 12px;
          border-bottom: 1px solid var(--divider-color);
        }

        .control-button {
          padding: 4px 8px;
          background: none;
          border: 1px solid var(--primary-color);
          border-radius: 4px;
          color: var(--primary-color);
          cursor: pointer;
          font-size: 12px;
        }

        .control-button:hover {
          background: var(--primary-color);
          color: var(--text-primary-color);
        }

        .items-container {
          max-height: 300px;
          overflow-y: auto;
        }

        .item {
          display: flex;
          align-items: center;
          padding: 8px 12px;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .item:hover:not(.header) {
          background-color: var(--secondary-background-color);
        }

        .item.header {
          font-weight: bold;
          color: var(--secondary-text-color);
          cursor: default;
          font-size: 12px;
          padding: 6px 12px;
          background-color: var(--divider-color);
        }

        .item input[type="checkbox"] {
          margin-right: 8px;
        }

        .item-label {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .selected-count {
          margin-top: 8px;
          font-size: 14px;
          color: var(--secondary-text-color);
        }

        .search-icon {
          position: absolute;
          right: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--secondary-text-color);
        }
      </style>

      <div class="search-container">
        <input 
          type="text" 
          id="search-input" 
          placeholder="${this.getAttribute('placeholder') || 'Search...'}"
          value="${this._searchTerm}"
        >
        <span class="search-icon">🔍</span>
      </div>

      <div class="dropdown">
        <div class="controls">
          <button class="control-button" id="select-all">Select All Visible</button>
          <button class="control-button" id="select-none">Clear Selection</button>
        </div>
        <div class="items-container">
          ${this.renderItems()}
        </div>
      </div>

      <div class="selected-count">
        ${this._selected.size} selected
      </div>
    `;
  }

  renderItems() {
    const filtered = this.getFilteredItems();
    const container = this.shadowRoot.querySelector('.items-container');
    
    if (container) {
      container.innerHTML = filtered.map(item => {
        if (item.disabled) {
          return `<div class="item header">${item.label}</div>`;
        }

        const isSelected = this._selected.has(item.value);
        return `
          <div class="item" data-value="${item.value}">
            <input 
              type="checkbox" 
              ${isSelected ? 'checked' : ''}
              data-value="${item.value}"
            >
            <span class="item-label">${item.label}</span>
          </div>
        `;
      }).join('');

      // Add click handlers to new items
      container.querySelectorAll('.item:not(.header)').forEach(item => {
        item.addEventListener('click', (e) => {
          if (e.target.type !== 'checkbox') {
            const value = item.dataset.value;
            this.toggleItem(value);
          }
        });
      });

      container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', (e) => {
          const value = e.target.dataset.value;
          this.toggleItem(value);
        });
      });
    }

    return '';
  }
}

// Register the custom element
customElements.define('searchable-select', SearchableSelect);

// Export for use in Home Assistant frontend
export { SearchableSelect };