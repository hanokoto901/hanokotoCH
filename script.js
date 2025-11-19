// はのこと活動記録 - Web公開用スクリプト
// コメントを簡潔化（作業ログ的コメントを整理）

document.addEventListener('DOMContentLoaded', () => {
	const tabs = document.querySelectorAll('.tab');
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
		// タブ種別に色を同期
		tabsContainer.dataset.active = tab.dataset.class || '';
	};

	// タブをアクティブ化（必要に応じてフォーカス移動）
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
		
		// タブごとの検索バー表示切替
		document.querySelectorAll('.timeline-search-bar').forEach((bar, i) => {
			if (i === index) bar.classList.add('active');
			else bar.classList.remove('active');
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

	// 初期アクティブタブ
	const initialIndex = Array.from(tabs).findIndex(t => t.classList.contains('active'));
	activateTab(initialIndex >= 0 ? initialIndex : 0, { focus: false });

	// 年表検索バーの生成（タブ直後に配置）
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

		// 行フィルタリング
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

	// 年表用「上部に戻る」ボタンを安全に隠す
	const hideBackToTableTop = () => {
		const btn = document.querySelector('.back-to-table-top');
		if (btn) btn.classList.remove('show');
	};

	// アクティブな年表スクロール要素
	const getActiveTable = () => document.querySelector('.tab-content.active .table-responsive');

	// ナビゲーション表示切替
	const showSection = (sectionId) => {
		// メニュー切替時に年表用ボタンを非表示
		hideBackToTableTop();

		sections.forEach(section => section.classList.remove('active'));
		
		navLinks.forEach(link => {
			if (link.dataset.section === sectionId) {
				link.style.background = '#f0f0f0';
				link.setAttribute('aria-current', 'page');
			} else {
				link.style.background = '';
				link.removeAttribute('aria-current');
			}
		});

		const homeSectionEl = document.querySelector('.home-section');
		const videosSectionEl = document.getElementById('videos');
		// 歌みた紹介セクション取得
		const coversSectionEl = document.getElementById('covers');

		if (sectionId === 'home') {
			// ホーム表示
			if (homeSectionEl) homeSectionEl.classList.add('active');
			if (tabsContainer) tabsContainer.style.display = 'flex';
			if (searchBarsContainer) searchBarsContainer.style.display = 'block';
			const current = Array.from(tabs).findIndex(t => t.classList.contains('active'));
			const idx = current >= 0 ? current : 0;
			activateTab(idx, { focus: false });
		} else if (sectionId === 'videos') {
			// 切り抜き紹介
			if (homeSectionEl) homeSectionEl.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
			tabContents.forEach(content => content.style.display = 'none');
			if (videosSectionEl) videosSectionEl.classList.add('active');

			// 表示直後にわずかにスクロールして矢印を有効化
			requestAnimationFrame(() => {
				document.querySelectorAll('.videos-carousel-wrapper .videos-carousel').forEach(c => {
					if (c.scrollWidth > c.clientWidth) {
						c.scrollTo({ left: Math.max(2, c.scrollLeft) });
						c.dispatchEvent(new Event('scroll'));
					}
				});
			});
		} else if (sectionId === 'covers') {
			// 歌みた紹介（切り抜き紹介と同様）
			if (homeSectionEl) homeSectionEl.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
			tabContents.forEach(content => content.style.display = 'none');
			if (coversSectionEl) coversSectionEl.classList.add('active');

			requestAnimationFrame(() => {
				document.querySelectorAll('.videos-carousel-wrapper .videos-carousel').forEach(c => {
					if (c.scrollWidth > c.clientWidth) {
						c.scrollTo({ left: Math.max(2, c.scrollLeft) });
						c.dispatchEvent(new Event('scroll'));
					}
				});
			});
		} else {
			// その他セクション
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

	// 初期状態: ホーム
	showSection('home');

	// インジケーター追従（リサイズ・横スクロール）
	const syncCurrentIndicator = () => {
		const current = Array.from(tabs).findIndex(t => t.classList.contains('active'));
		updateIndicator(current >= 0 ? current : 0);
	};
	let resizeRaf = null;
	window.addEventListener('resize', () => {
		if (resizeRaf) return;
		resizeRaf = requestAnimationFrame(() => {
			syncCurrentIndicator();
			resizeRaf = null;
		});
	});
	if (tabsContainer) tabsContainer.addEventListener('scroll', syncCurrentIndicator, { passive: true });

	// トップへ戻る（ページ全体）
	const backToTop = document.createElement('button');
	backToTop.className = 'back-to-top';
	backToTop.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
	backToTop.setAttribute('aria-label', 'ページトップへ戻る');
	document.body.appendChild(backToTop);

	// トップへ戻る（年表）
	const backToTableTop = document.createElement('button');
	backToTableTop.className = 'back-to-table-top';
	backToTableTop.innerHTML = '<i class="fa-solid fa-arrow-up"></i>';
	backToTableTop.setAttribute('aria-label', '年表トップへ戻る');
	document.body.appendChild(backToTableTop);

	// ページ全体のスクロール監視
	const toggleBackToTop = () => {
		if (window.scrollY > 300) {
			backToTop.classList.add('show');
		} else {
			backToTop.classList.remove('show');
		}
	};

	// 年表のスクロール監視
	const toggleBackToTableTop = () => {
		const activeTable = document.querySelector('.tab-content.active .table-responsive');
		const tableScroll = activeTable ? activeTable.scrollTop : 0;
		
		if (tableScroll > 300) {
			backToTableTop.classList.add('show');
		} else {
			backToTableTop.classList.remove('show');
		}
	};

	// クリック動作
	backToTop.addEventListener('click', () => {
		window.scrollTo({ top: 0, behavior: 'smooth' });
	});
	backToTableTop.addEventListener('click', () => {
		const activeTable = getActiveTable();
		if (activeTable) {
			activeTable.scrollTo({ top: 0, behavior: 'smooth' });
		}
	});

	// スクロール監視（passive）
	window.addEventListener('scroll', toggleBackToTop, { passive: true });
	document.querySelectorAll('.table-responsive').forEach(table => {
		table.addEventListener('scroll', toggleBackToTableTop, { passive: true });
	});

	// 動画カルーセル
	document.querySelectorAll('.videos-carousel-wrapper').forEach(wrapper => {
		const carousel = wrapper.querySelector('.videos-carousel');
		const prevBtn = wrapper.querySelector('.carousel-btn.prev');
		const nextBtn = wrapper.querySelector('.carousel-btn.next');
		
		if (!carousel || !prevBtn || !nextBtn) return;
		
		const scrollAmount = 300; // 1回のスクロール量
		
		prevBtn.addEventListener('click', () => {
			carousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
		});
		
		nextBtn.addEventListener('click', () => {
			carousel.scrollBy({ left: scrollAmount, behavior: 'smooth' });
		});
		
		// ボタンの有効/無効を制御
		const updateButtons = () => {
			const { scrollLeft, scrollWidth, clientWidth } = carousel;
			const isAtStart = scrollLeft <= 1;
			const isAtEnd = scrollLeft >= scrollWidth - clientWidth - 1;
			prevBtn.disabled = isAtStart;
			nextBtn.disabled = isAtEnd;
		};
		
		carousel.addEventListener('scroll', updateButtons);
		window.addEventListener('resize', updateButtons);
		updateButtons(); // 初期状態を設定

		// 初期化直後にわずかにスクロールして前へボタンを有効化
		requestAnimationFrame(() => {
			if (carousel.scrollWidth > carousel.clientWidth) {
				carousel.scrollTo({ left: 2 });
				updateButtons();
			}
		});
	});

	// ハンバーガーメニュー（モバイル）
	const menuToggle = document.createElement('button');
	menuToggle.className = 'menu-toggle';
	menuToggle.setAttribute('aria-label', 'メニューを開く');
	menuToggle.innerHTML = '<span></span><span></span><span></span>';
	
	const headerLeft = document.querySelector('.header-left');
	const headerNav = document.querySelector('.header-nav');
	
	if (headerLeft && headerNav) {
		headerLeft.appendChild(menuToggle);
		
		menuToggle.addEventListener('click', () => {
			const isOpen = headerNav.classList.toggle('open');
			menuToggle.classList.toggle('active');
			menuToggle.setAttribute('aria-label', isOpen ? 'メニューを閉じる' : 'メニューを開く');
			menuToggle.setAttribute('aria-expanded', isOpen);
		});
		
		// メニューリンククリック時に自動で閉じる
		navLinks.forEach(link => {
			link.addEventListener('click', () => {
				if (window.innerWidth <= 768) {
					headerNav.classList.remove('open');
					menuToggle.classList.remove('active');
					menuToggle.setAttribute('aria-label', 'メニューを開く');
					menuToggle.setAttribute('aria-expanded', 'false');
				}
			});
		});
		
		// 画面外タップでメニューを閉じる
		document.addEventListener('click', (e) => {
			if (window.innerWidth <= 768 && 
			    headerNav.classList.contains('open') &&
			    !headerNav.contains(e.target) &&
			    !menuToggle.contains(e.target)) {
				headerNav.classList.remove('open');
				menuToggle.classList.remove('active');
				menuToggle.setAttribute('aria-label', 'メニューを開く');
				menuToggle.setAttribute('aria-expanded', 'false');
			}
		});
	}
});
