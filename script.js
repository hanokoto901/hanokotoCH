document.addEventListener('DOMContentLoaded', () => {
	const tabs = document.querySelectorAll('.tab');
	// const panels = document.querySelectorAll('.tab-content'); // 削除: 重複
	const navLinks = document.querySelectorAll('.nav-link');
	const sections = document.querySelectorAll('.section');
	const tabsContainer = document.querySelector('.tabs');
	const tabContents = document.querySelectorAll('.tab-content');

	if (!tabs.length) return;

	// インジケーター生成
	const indicator = document.createElement('div');
	indicator.className = 'tab-indicator';
	if (tabsContainer) tabsContainer.appendChild(indicator);

	// インジケーター位置更新
	const updateIndicator = (index) => {
		if (!tabsContainer || !indicator) return;
		const tab = tabs[index];
		if (!tab) return;
		const left = tab.offsetLeft - tabsContainer.scrollLeft;
		const width = tab.offsetWidth;
		indicator.style.left = left + 'px';
		indicator.style.width = width + 'px';
		// インジケーター色をタブ種別に同期
		tabsContainer.dataset.active = tab.dataset.class || '';
	};

	// タブをアクティブ化（オプションでフォーカス可）
	const activateTab = (index, { focus = false } = {}) => {
		tabs.forEach((tab, i) => {
			const isActive = i === index;
			tab.classList.toggle('active', isActive);
			tab.setAttribute('aria-selected', isActive);
			tab.setAttribute('tabindex', isActive ? '0' : '-1');
		});
		// panels → tabContents に統一
		tabContents.forEach((panel, i) => {
			const isVisible = i === index;
			panel.classList.toggle('active', isVisible);
			panel.setAttribute('aria-hidden', !isVisible);
			panel.style.display = isVisible ? 'block' : 'none';
		});
		
		// 検索バーの表示/非表示を切り替え
		document.querySelectorAll('.timeline-search-bar').forEach((bar, i) => {
			if (i === index) {
				bar.classList.add('active');
			} else {
				bar.classList.remove('active');
			}
		});
		
		tabs[index].scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
		updateIndicator(index);
		if (focus) tabs[index].focus({ preventScroll: true });
	};

	// キー操作のハンドラーマップ
	const keyHandlers = {
		ArrowRight: (i) => (i + 1) % tabs.length,
		ArrowLeft: (i) => (i - 1 + tabs.length) % tabs.length,
		Home: () => 0,
		End: () => tabs.length - 1,
		Enter: (i) => i,
		' ': (i) => i
	};

	// イベントリスナーを設定
	tabs.forEach((tab, i) => {
		tab.addEventListener('click', () => activateTab(i, { focus: false }));
		tab.addEventListener('keydown', (e) => {
			const handler = keyHandlers[e.key];
			if (handler) {
				e.preventDefault();
				// キーボード操作時はフォーカスを当てる（フォーカスリング表示）
				activateTab(handler(i), { focus: true });
			}
		});
	});

	// 初期アクティブタブ（フォーカスなし）
	const initialIndex = Array.from(tabs).findIndex(t => t.classList.contains('active'));
	activateTab(initialIndex >= 0 ? initialIndex : 0, { focus: false });

	// 年表検索バーの生成（タブコンテナの直後に配置）
	const searchBarsContainer = document.createElement('div');
	if (tabsContainer && tabsContainer.parentNode) {
		tabsContainer.parentNode.insertBefore(searchBarsContainer, tabsContainer.nextSibling);
	}

	// 検索機能の初期化
	const initializeSearch = (tabContent, tabIndex) => {
		const searchBar = document.createElement('div');
		searchBar.className = 'timeline-search-bar';
		if (tabIndex === 0) searchBar.classList.add('active');
		
		searchBar.innerHTML = `
			<div class="timeline-search-wrapper">
				<input type="text" placeholder="キーワードで検索（年・月・内容）" />
				<button type="button" class="timeline-search-clear" title="クリア">
					<i class="fa fa-times"></i>
				</button>
			</div>
		`;
		searchBarsContainer.appendChild(searchBar);

		const input = searchBar.querySelector('input');
		const clearButton = searchBar.querySelector('.timeline-search-clear');
		const tbody = tabContent.querySelector('table tbody');

		// 年グループ処理（rowspan対応）
		const processYearGroup = (rows, keyword) => {
			const hasMatch = rows.some(row => 
				!keyword || row.textContent.toLowerCase().includes(keyword)
			);

			rows.forEach(row => {
				row.style.display = hasMatch ? "" : "none";
				
				if (hasMatch && keyword) {
					Array.from(row.cells).forEach(cell => {
						const match = cell.textContent.toLowerCase().includes(keyword);
						cell.classList.toggle('timeline-highlight', match);
					});
				} else {
					Array.from(row.cells).forEach(cell => 
						cell.classList.remove('timeline-highlight')
					);
				}
			});
		};

		// フィルタリング実行
		const filterRows = () => {
			const keyword = input.value.trim().toLowerCase();
			if (!tbody) return;

			// 前回の「該当なし」メッセージを削除
			tabContent.querySelector('.timeline-no-result')?.remove();

			// 年ごとにグループ化して処理
			let currentYearRows = [];
			let visibleCount = 0;

			Array.from(tbody.rows).forEach(row => {
				const hasYearCell = row.cells[0]?.hasAttribute('rowspan');

				if (hasYearCell && currentYearRows.length > 0) {
					processYearGroup(currentYearRows, keyword);
					currentYearRows = [];
				}
				currentYearRows.push(row);
			});

			if (currentYearRows.length > 0) {
				processYearGroup(currentYearRows, keyword);
			}

			// 表示件数カウント
			visibleCount = Array.from(tbody.rows).filter(
				row => row.style.display !== 'none'
			).length;

			// 0件メッセージ表示
			if (visibleCount === 0 && keyword) {
				const noResult = document.createElement('div');
				noResult.className = 'timeline-no-result';
				noResult.textContent = '該当する年表データがありません。';
				tabContent.appendChild(noResult);
			}
		};

		// ×ボタン表示切替
		const toggleClearButton = () => {
			clearButton.classList.toggle('show', !!input.value.trim());
		};

		// イベントリスナー
		input.addEventListener('input', () => {
			toggleClearButton();
			filterRows();
		});

		clearButton.addEventListener('click', () => {
			input.value = '';
			toggleClearButton();
			filterRows();
			input.focus();
		});

		toggleClearButton();
	};

	// 各タブに検索機能を適用
	tabContents.forEach(initializeSearch);

	// ナビゲーションリンクの処理
	const showSection = (sectionId) => {
		sections.forEach(section => section.classList.remove('active'));
		
		navLinks.forEach(link => {
			if (link.dataset.section === sectionId) {
				link.style.background = '#f0f0f0';
			} else {
				link.style.background = '';
			}
		});

		const homeSectionEl = document.querySelector('.home-section');

		if (sectionId === 'home') {
			// ホーム表示
			if (homeSectionEl) homeSectionEl.classList.add('active');
			if (tabsContainer) tabsContainer.style.display = 'flex';
			if (searchBarsContainer) searchBarsContainer.style.display = 'block';
			const current = Array.from(tabs).findIndex(t => t.classList.contains('active'));
			const idx = current >= 0 ? current : 0;
			activateTab(idx, { focus: false });
		} else {
			// 他セクション表示
			if (homeSectionEl) homeSectionEl.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
			tabContents.forEach(content => content.style.display = 'none');
			const targetSection = document.getElementById(sectionId);
			if (targetSection) targetSection.classList.add('active');
		}
	};

	navLinks.forEach(link => {
		link.addEventListener('click', (e) => {
			e.preventDefault();
			const sectionId = link.dataset.section;
			showSection(sectionId);
		});
	});

	// 初期状態: ホームを表示
	showSection('home');

	// 削除: 未使用（Googleフォームはリンク遷移のためiframe高さ調整は不要）
	// window.addEventListener('message', (e) => {
	// 	if (e.origin === 'https://docs.google.com') {
	// 		const iframe = document.querySelector('.google-form-container iframe');
	// 		if (iframe && e.data && e.data.height) {
	// 			iframe.style.height = e.data.height + 'px';
	// 		}
	// 	}
	// });

	// インジケーター追従（リサイズ・横スクロール時）
	const syncCurrentIndicator = () => {
		const current = Array.from(tabs).findIndex(t => t.classList.contains('active'));
		updateIndicator(current >= 0 ? current : 0);
	};
	window.addEventListener('resize', syncCurrentIndicator);
	if (tabsContainer) tabsContainer.addEventListener('scroll', syncCurrentIndicator);
});
