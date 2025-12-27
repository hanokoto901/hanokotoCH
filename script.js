// はのこと活動記録 - Web公開用スクリプト
// コメントを簡潔化（作業ログ的コメントを整理）

document.addEventListener('DOMContentLoaded', () => {
	const tabs = document.querySelectorAll('.tab');
	const navLinks = document.querySelectorAll('.nav-link');
	const sections = document.querySelectorAll('.section');
	const tabsContainer = document.querySelector('.tabs');
	const tabContents = document.querySelectorAll('.tab-content');

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
			// 不要なインラインdisplay操作を削除（CSS制御に統一）
			// panel.style.display = isVisible ? 'block' : 'none';
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

	// 追加: ライブセクション初期化（一覧→詳細切替）
	let concertInitialized = false;
	const initConcertSection = () => {
		if (concertInitialized) return;
		const concertSection = document.getElementById('concert');
		if (!concertSection) return;

		const items = concertSection.querySelectorAll('.concert-item');
		const panels = concertSection.querySelectorAll('.concert-detail-panel');

		// 追加: ツアー開閉初期化（デフォルト閉）
		const groups = concertSection.querySelectorAll('.concert-group');
		groups.forEach(g => {
			g.classList.remove('open');
			const ul = g.querySelector('.concert-items');
			if (ul) ul.hidden = true;
			const btn = g.querySelector('.concert-toggle');
			if (btn) btn.setAttribute('aria-expanded', 'false');
		});
		// 追加: トグルイベント
		concertSection.querySelectorAll('.concert-toggle').forEach(btn => {
			btn.addEventListener('click', () => {
				const group = btn.closest('.concert-group');
				const ul = group?.querySelector('.concert-items');
				const expanded = btn.getAttribute('aria-expanded') === 'true';
				btn.setAttribute('aria-expanded', (!expanded).toString());
				group?.classList.toggle('open', !expanded);
				if (ul) ul.hidden = expanded; // 開: false / 閉: true
			});
		});

		const activate = (id) => {
			let found = false;
			items.forEach(li => {
				const match = li.dataset.concertId === String(id);
				li.classList.toggle('active', match);
				if (match) found = true;
			});
			panels.forEach(p => {
				p.classList.toggle('active', p.dataset.concertId === String(id));
			});
			if (!found && items.length) {
				const firstId = items[0].dataset.concertId;
				items[0].classList.add('active');
				concertSection.querySelector(`#concert-detail-${firstId}`)?.classList.add('active');
			}
		};

		items.forEach(li => {
			li.addEventListener('click', () => activate(li.dataset.concertId));
			li.addEventListener('keydown', (e) => {
				if (e.key === 'Enter' || e.key === ' ') {
					e.preventDefault();
					activate(li.dataset.concertId);
				}
			});
		});

		// 既にactiveなパネルがあればそれに同期、なければ先頭を表示
		const activePanel = concertSection.querySelector('.concert-detail-panel.active');
		if (activePanel) {
			activate(activePanel.dataset.concertId);
		} else if (items.length) {
			activate(items[0].dataset.concertId);
		}

		concertInitialized = true;
	};

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

	// 共通: カルーセル矢印有効化のための微スクロール（重複削除）
	const nudgeCarousels = () => {
		requestAnimationFrame(() => {
			document.querySelectorAll('.videos-carousel-wrapper .videos-carousel').forEach(c => {
				if (c.scrollWidth > c.clientWidth) {
					c.scrollTo({ left: Math.max(2, c.scrollLeft) });
					c.dispatchEvent(new Event('scroll'));
				}
			});
		});
	};

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
		// 歌動画紹介セクション取得
		const coversSectionEl = document.getElementById('covers');

		if (sectionId === 'home') {
			// ホーム表示
			if (homeSectionEl) homeSectionEl.classList.add('active');
			if (tabsContainer) tabsContainer.style.display = 'flex';
			if (searchBarsContainer) searchBarsContainer.style.display = 'block';
			// タブが存在する時のみアクティブ化
			if (tabs.length) {
				const current = Array.from(tabs).findIndex(t => t.classList.contains('active'));
				const idx = current >= 0 ? current : 0;
				activateTab(idx, { focus: false });
			}
		} else if (sectionId === 'videos') {
			// 切り抜き紹介
			if (homeSectionEl) homeSectionEl.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
			if (videosSectionEl) videosSectionEl.classList.add('active');

			nudgeCarousels();
			initClipsListSection();
		} else if (sectionId === 'covers') {
			// 歌動画紹介（切り抜き紹介と同様）
			if (homeSectionEl) homeSectionEl.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
			if (coversSectionEl) coversSectionEl.classList.add('active');

			nudgeCarousels();
			initCoversListSection();
		} else if (sectionId === 'concert') {
			// ライブ（左右分割）
			const homeSectionElLocal = document.querySelector('.home-section');
			if (homeSectionElLocal) homeSectionElLocal.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
			const concertSection = document.getElementById('concert');
			if (concertSection) {
				concertSection.classList.add('active');
				initConcertSection();
			}
		} else if (sectionId === 'music') {
			// リリース
			const homeSectionElLocal = document.querySelector('.home-section');
			if (homeSectionElLocal) homeSectionElLocal.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
			const musicSection = document.getElementById('music');
			if (musicSection) {
				musicSection.classList.add('active');

				// 追加: 復元リクエストがある場合、ラジオ初期選択を先に適用
				const params = new URLSearchParams(location.search);
				const shouldRestore = params.get('restore') === 'music';
				if (shouldRestore) {
					const state = getSavedMusicState();
					if (state) {
						const controls = musicSection.querySelector('#release-songs-controls');
						if (controls) {
							const singerRadio = controls.querySelector(`input[name="release-singer"][value="${state.singer}"]`);
							const kindRadio = controls.querySelector(`input[name="release-kind"][value="${state.kind}"]`);
							if (singerRadio) singerRadio.checked = true;
							if (kindRadio) kindRadio.checked = true;
						}
					}
				}

				nudgeCarousels();           // アルバム/シングルのカルーセル用
				initReleaseSongsFilters();  // 楽曲フィルター初期化

				// 追加: フィルター適用後にスクロール位置を復元
				const params2 = new URLSearchParams(location.search);
				if (params2.get('restore') === 'music') {
					const state = getSavedMusicState();
					if (state && typeof state.scrollY === 'number') {
						requestAnimationFrame(() => {
							window.scrollTo({ top: state.scrollY, behavior: 'auto' });
						});
					}
					// URLのrestoreパラメータを消しておく（履歴を汚さない）
					try {
						const url = new URL(location.href);
						url.searchParams.delete('restore');
						history.replaceState({}, '', url.toString());
					} catch {}
					// 一度復元したら保存値はクリア
					clearSavedMusicState();
				}
			}
		} else {
			// その他セクション
			if (homeSectionEl) homeSectionEl.classList.remove('active');
			if (tabsContainer) tabsContainer.style.display = 'none';
			if (searchBarsContainer) searchBarsContainer.style.display = 'none';
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

	// 初期状態: URLのハッシュ/クエリに応じて開始セクションを決定
	const params = new URLSearchParams(location.search);
	const initialSection = params.get('restore') === 'music'
		? 'music'
		: (location.hash ? location.hash.replace('#', '') : 'home');
	showSection(initialSection);

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
		const activeTable = getActiveTable();
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

	// 追加: 歌動画一覧（ALL）フィルター・ソート初期化
	let coversListInitialized = false;
	const initCoversListSection = () => {
		if (coversListInitialized) return;
		const coversSection = document.getElementById('covers');
		if (!coversSection) return;
		const grid = coversSection.querySelector('#covers-all-grid');
		if (!grid) return;

		const cards = Array.from(grid.querySelectorAll('.song-card'));
		const tagGroup = coversSection.querySelector('[role="group"][aria-label="チャンネル種別でフィルター"]');
		const sortSelect = coversSection.querySelector('.covers-sort-key');
		// 追加: キーワード検索
		const searchInput = coversSection.querySelector('.covers-search');
		const clearBtn = coversSection.querySelector('.covers-search-clear');

		// ラジオボタン群
		const tagRadios = tagGroup ? Array.from(tagGroup.querySelectorAll('input[type="radio"]')) : [];

		// フィルター: data-tag + キーワード
		const applyFilter = () => {
			const tagVal = tagGroup ? (tagGroup.querySelector('input[type="radio"]:checked')?.value || 'all') : 'all';
			const q = (searchInput?.value || '').trim().toLowerCase();

			cards.forEach(card => {
				const tagOk = (tagVal === 'all') ? true : ((card.dataset.tag || '') === tagVal);
				const title = (card.dataset.title || '').toLowerCase();
				const textOk = !q || title.includes(q);
				card.style.display = (tagOk && textOk) ? '' : 'none';
			});
		};

		// 並び替え（既存のまま）
		const applySort = () => {
			if (!sortSelect) return;
			const val = sortSelect.value;
			const cmp = (a, b) => {
				const ad = a.dataset.date ? new Date(a.dataset.date).getTime() : 0;
				const bd = b.dataset.date ? new Date(b.dataset.date).getTime() : 0;
				const av = parseInt(a.dataset.views || '0', 10);
				const bv = parseInt(b.dataset.views || '0', 10);
				const ap = parseInt(a.dataset.popularity || '0', 10);
				const bp = parseInt(b.dataset.popularity || '0', 10);
				switch (val) {
					case 'date_desc': return bd - ad;
					case 'date_asc': return ad - bd;
					case 'views_desc': return bv - av;
					case 'views_asc': return av - bv;
					case 'popularity_desc': return bp - ap;
					default: return 0;
				}
			};
			const visibleCards = cards.filter(c => c.style.display !== 'none');
			visibleCards.sort(cmp).forEach(c => grid.appendChild(c));
		};

		// ラベルのactive同期（選択中のみactive）
		const syncActiveLabels = () => {
			if (!tagGroup) return;
			const checked = tagGroup.querySelector('input[type="radio"]:checked');
			tagGroup.querySelectorAll('label').forEach(label => {
				label.classList.toggle('active', !!checked && label.contains(checked));
			});
		};

		tagRadios.forEach(rb => {
			rb.addEventListener('change', () => {
				syncActiveLabels();
				applyFilter();
				applySort();
			});
		});
		if (sortSelect) sortSelect.addEventListener('change', applySort);

		// 追加: 検索イベント
		const toggleClear = () => {
			if (clearBtn) clearBtn.classList.toggle('show', !!searchInput?.value.trim());
		};
		if (searchInput) searchInput.addEventListener('input', () => { toggleClear(); applyFilter(); });
		if (clearBtn) clearBtn.addEventListener('click', () => {
			if (!searchInput) return;
			searchInput.value = '';
			toggleClear();
			applyFilter();
			searchInput.focus();
		});

		// 初期同期
		syncActiveLabels();
		applyFilter();
		applySort();
		toggleClear();

		coversListInitialized = true;
	};

	// 追加: リリース楽曲一覧（歌唱・種別・キーワードフィルター）
	let releaseSongsInitialized = false;
	const initReleaseSongsFilters = () => {
		if (releaseSongsInitialized) return;
		const musicSection = document.getElementById('music');
		if (!musicSection) return;
		const grid = musicSection.querySelector('#release-songs-grid');
		const controls = musicSection.querySelector('#release-songs-controls');
		if (!grid || !controls) return;

		const cards = Array.from(grid.querySelectorAll('.song-card'));
		const singerGroup = controls.querySelector('[role="group"][aria-label="歌唱でフィルター"]');
		const kindGroup = controls.querySelector('[role="group"][aria-label="種別でフィルター"]');
		// 追加: キーワード検索
		const searchInput = controls.querySelector('.release-search');
		const clearBtn = controls.querySelector('.release-search-clear');

		// ラジオボタン群
		const singerRadios = singerGroup ? Array.from(singerGroup.querySelectorAll('input[type="radio"]')) : [];
		const kindRadios = kindGroup ? Array.from(kindGroup.querySelectorAll('input[type="radio"]')) : [];

		const applyFilter = () => {
			const singerVal = singerGroup ? (singerGroup.querySelector('input[type="radio"]:checked')?.value || 'all') : 'all';
			const kindVal = kindGroup ? (kindGroup.querySelector('input[type="radio"]:checked')?.value || 'all') : 'all';
			const q = (searchInput?.value || '').trim().toLowerCase();

			cards.forEach(card => {
				const hasUnit = card.dataset.unit === '1';
				const hasHanon = card.dataset.hanon === '1';
				const hasKotoha = card.dataset.kotoha === '1';

				let singerMatch = true;
				if (singerVal !== 'all') {
					if (singerVal === 'unit') singerMatch = hasUnit || (hasHanon && hasKotoha);
					else if (singerVal === 'hanon') singerMatch = hasHanon;
					else if (singerVal === 'kotoha') singerMatch = hasKotoha;
				}

				const kindCode = card.dataset.kind || 'other';
				const kindMatch = (kindVal === 'all') ? true : (kindCode === kindVal);

				const title = (card.dataset.title || '').toLowerCase();
				const textMatch = !q || title.includes(q);

				card.style.display = (singerMatch && kindMatch && textMatch) ? '' : 'none';
			});
		};

		// ラベルのactive同期（選択中のみactive）
		const syncActiveLabels = () => {
			[singerGroup, kindGroup].forEach(group => {
				if (!group) return;
				const checked = group.querySelector('input[type="radio"]:checked');
				group.querySelectorAll('label').forEach(label => {
					label.classList.toggle('active', !!checked && label.contains(checked));
				});
			});
		};

		[...singerRadios, ...kindRadios].forEach(rb => {
			rb.addEventListener('change', () => {
				syncActiveLabels();
				applyFilter();
			});
		});

		// 追加: 検索イベント
		const toggleClear = () => {
			if (clearBtn) clearBtn.classList.toggle('show', !!searchInput?.value.trim());
		};
		if (searchInput) searchInput.addEventListener('input', () => { toggleClear(); applyFilter(); });
		if (clearBtn) clearBtn.addEventListener('click', () => {
			if (!searchInput) return;
			searchInput.value = '';
			toggleClear();
			applyFilter();
			searchInput.focus();
		});

		// 初期同期
		syncActiveLabels();
		applyFilter();
		toggleClear();

		releaseSongsInitialized = true;
	};

	// 追加: リリースセクションの状態保存/復元
	const MUSIC_STATE_KEY = 'musicState';

	const saveMusicState = () => {
		const musicSection = document.getElementById('music');
		if (!musicSection) return;
		const controls = musicSection.querySelector('#release-songs-controls');
		if (!controls) return;
		const singer = controls.querySelector('input[name="release-singer"]:checked')?.value || 'all';
		const kind = controls.querySelector('input[name="release-kind"]:checked')?.value || 'all';
		const scrollY = window.scrollY || 0;
		const state = { singer, kind, scrollY };
		try {
			sessionStorage.setItem(MUSIC_STATE_KEY, JSON.stringify(state));
		} catch {}
	};

	const getSavedMusicState = () => {
		try {
			const raw = sessionStorage.getItem(MUSIC_STATE_KEY);
			return raw ? JSON.parse(raw) : null;
		} catch {
			return null;
		}
	};

	const clearSavedMusicState = () => {
		try { sessionStorage.removeItem(MUSIC_STATE_KEY); } catch {}
	};

	// 楽曲/アルバム/シングル詳細へ遷移する直前に状態保存（イベント委譲）
	const attachMusicStateSavers = () => {
		const musicSection = document.getElementById('music');
		if (!musicSection) return;
		musicSection.addEventListener('click', (e) => {
			const a = e.target.closest('a');
			if (!a) return;
			const href = a.getAttribute('href') || '';
			// songs/ または CDs/ に遷移するリンクのみ保存
			if (href.startsWith('songs/') || href.startsWith('CDs/')) {
				saveMusicState();
			}
		});
	};

	// 初期化
	initCoversListSection();
	initClipsListSection();
	initReleaseSongsFilters();
	attachMusicStateSavers(); // 追加: 遷移前に状態を保存
});
